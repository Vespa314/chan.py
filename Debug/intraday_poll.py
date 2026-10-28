# -*- coding: utf-8 -*-
"""
盘中分钟级接入引擎：短周期轮询拉取已收盘 bar → 幂等落库 → 水位通知重算。

对应 openspec 变更 persist-kl-to-duckdb 的 D7 / D12 / D14：
- 轮询间隔默认 1 分钟，仅在交易时段运行（收盘后补拉收尾由外部 cron 负责）。
- 只持久化并计算「已收盘」bar（time_key ≤ now）；形成中的 bar 不进计算。
- 新 bar 落库 → DuckDB 表内水位 max(time_key) 前进 → 推进 last_processed_time 游标
  （存 PG，见 DataAPI/RecomputeCursor.py）→ 触发重算。
- 限频（poll_interval 间隔）、指数退避、单股票失败隔离。

用法：
    python Debug/intraday_poll.py --config ingest_config.json --pg-dsn "host=... dbname=..."
    python Debug/intraday_poll.py --config ingest_config.json --once     # 单轮（测试/手动补拉）
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import pandas as pd

from Common.CEnum import KL_TYPE
from DataAPI.IngestUtil import iter_ingest_jobs, klu_to_row, load_config, validate
from DataAPI.KLineStore import KLineStore, DEFAULT_DB_PATH
from DataAPI.RecomputeCursor import MemoryCursor, RecomputeCursor

log = logging.getLogger("intraday_poll")

BACKOFF_BASE = 2.0  # 指数退避基数（秒），封顶 64 * BASE


# ---------------------------------------------------------------------------
# 交易时段与已收盘判定
# ---------------------------------------------------------------------------
def is_in_session(now: datetime, sessions) -> bool:
    """now 是否落在任一交易时段内；sessions 形如 [["09:30","11:30"],["13:00","15:00"]]。"""
    hm = now.strftime("%H:%M")
    return any(s <= hm <= e for s, e in sessions)


def filter_closed_bars(df: pd.DataFrame, now: str) -> pd.DataFrame:
    """只保留已收盘 bar：time_key（即 bar 收盘时刻）<= now。"""
    if df is None or df.empty:
        return df
    return df[df["time_key"] <= now]


# ---------------------------------------------------------------------------
# 拉取与落库
# ---------------------------------------------------------------------------
def poll_once(minute_cls, code, k_type, autype, store: KLineStore, now: str, begin=None):
    """拉取一次分钟线、过滤未收盘 bar、校验、upsert，返回新水位（无新数据返回 None）。"""
    if begin is None:
        wm = store.max_time_key(code, k_type.name, autype.name)
        begin = wm or "2000-01-01 09:30:00"

    api = minute_cls(code=code, k_type=k_type, begin_date=begin, end_date=now, autype=autype)
    klus = list(api.get_kl_data())
    if not klus:
        return None

    df = pd.DataFrame([klu_to_row(k, code, k_type, autype) for k in klus])
    closed = filter_closed_bars(df, now)
    if closed.empty:
        return None

    valid, rejected, warns = validate(closed)
    for w in warns:
        log.warning("[%s] %s", code, w)
    if rejected:
        log.warning("[%s] 拒绝 %d 行非法数据", code, rejected)
    if not valid.empty:
        store.upsert(valid)
    return store.max_time_key(code, k_type.name, autype.name)


# ---------------------------------------------------------------------------
# 单轮：遍历所有股票，退避 + 失败隔离 + 重算通知
# ---------------------------------------------------------------------------
def iter_intraday_jobs(cfg: dict):
    """仅遍历分钟级 (code, kl_type, autype) 条目（盘中不处理日线及以上）。"""
    for code, kt, au in iter_ingest_jobs(cfg):
        if kt.value < KL_TYPE.K_DAY.value:
            yield code, kt, au


def run_once(cfg, store, minute_cls, cursor, recompute_fn, now, backoff=None, begin=None):
    """一轮拉取：对每只股票拉取已收盘 bar、落库、推进重算游标。

    单股失败不影响其余（隔离），并按指数退避延后重试。
    返回更新后的 backoff 状态字典。
    """
    backoff = backoff if backoff is not None else {}
    for code, kt, au in iter_intraday_jobs(cfg):
        key = (code, kt.name, au.name)
        bf = backoff.get(key)
        if bf and time.time() < bf["next_retry"]:
            continue  # 仍在退避窗口内，本轮跳过

        try:
            wm = poll_once(minute_cls, code, kt, au, store, now, begin=begin)
            if wm is not None:
                last = cursor.get(code, kt.name, au.name)
                if last is None or wm > last:
                    if recompute_fn is not None:
                        recompute_fn(code, kt, au)
                    cursor.set(code, kt.name, au.name, wm)
            backoff.pop(key, None)  # 成功即重置
        except Exception as e:
            log.error("[%s/%s/%s] 盘中拉取失败：%s", code, kt.name, au.name, e)
            bf = backoff.get(key, {"failures": 0, "next_retry": 0.0})
            bf["failures"] += 1
            bf["next_retry"] = time.time() + BACKOFF_BASE * (2 ** min(bf["failures"] - 1, 6))
            backoff[key] = bf
    return backoff


# ---------------------------------------------------------------------------
# 重算
# ---------------------------------------------------------------------------
def make_recompute(db_path):
    """构造默认重算函数：以 DuckDB 源离线跑 CChan，产出最新笔/段/买卖点。"""

    def recompute(code, k_type, autype):
        from DataAPI.DuckDBAPI import CDuckDB
        from Chan import CChan

        CDuckDB.db_path = db_path
        chan = CChan(code=code, data_src="custom:DuckDBAPI.CDuckDB",
                     lv_list=[k_type], autype=autype)
        kl = chan[k_type]
        log.info("[%s/%s] 重算完成：笔 %d 段 %d 买卖点 %d",
                 code, k_type.name, len(kl.bi_list), len(kl.seg_list), len(kl.bs_point_lst))

    return recompute


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------
def run_loop(cfg, store, minute_cls, cursor, recompute_fn=None, *,
             poll_interval=None, sessions=None, max_iterations=None, sleep_fn=time.sleep):
    """盘中轮询主循环：交易时段内反复 run_once，间隔 poll_interval 秒。"""
    poll_interval = poll_interval or cfg.get("poll_interval_seconds", 60)
    sessions = sessions or cfg.get("trading_sessions", [["09:30", "11:30"], ["13:00", "15:00"]])
    backoff = {}
    i = 0
    while True:
        now_dt = datetime.now()
        now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        if is_in_session(now_dt, sessions):
            backoff = run_once(cfg, store, minute_cls, cursor, recompute_fn, now, backoff=backoff)
        else:
            log.debug("非交易时段，跳过本轮")
        i += 1
        if max_iterations is not None and i >= max_iterations:
            break
        sleep_fn(poll_interval)


def main(argv=None):
    p = argparse.ArgumentParser(description="盘中分钟级接入 + 水位通知重算")
    p.add_argument("--config", required=True, help="JSON 配置文件路径")
    p.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB 库路径")
    p.add_argument("--pg-dsn", default=None, help="PostgreSQL 连接串；缺省用内存游标（测试）")
    p.add_argument("--once", action="store_true", help="只跑一轮后退出（而非常驻循环）")
    p.add_argument("--no-recompute", action="store_true", help="仅落库不触发重算")
    p.add_argument("--verbose", action="store_true", help="打印 DEBUG 日志")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config)
    db_path = cfg.get("db_path", args.db_path)

    # 分钟数据源：akshare 东财（延迟导入）
    from DataAPI.MinuteAPI import CMinute

    cursor = RecomputeCursor(args.pg_dsn) if args.pg_dsn else MemoryCursor()
    recompute_fn = None if args.no_recompute else make_recompute(db_path)

    with KLineStore(db_path) as store:
        if args.once:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_once(cfg, store, CMinute, cursor, recompute_fn, now)
        else:
            run_loop(cfg, store, CMinute, cursor, recompute_fn,
                     poll_interval=cfg.get("poll_interval_seconds", 60))
    return 0


if __name__ == "__main__":
    sys.exit(main())
