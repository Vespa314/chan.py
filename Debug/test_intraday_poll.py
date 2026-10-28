# -*- coding: utf-8 -*-
"""
盘中轮询引擎离线自测（tasks 5.2 / 5.3 / 5.4）。

用内存 DuckDB（:memory:）+ MemoryCursor + 伪分钟源，验证：
- 5.2 只持久化/计算「已收盘」bar，形成中的 bar 被排除；
- 5.3 新 bar 落库 → 水位前进 → 触发重算，且游标落独立 cursor（非 DuckDB 表）；
- 5.4 单股失败隔离 + 指数退避，其余股票不受影响。

运行：  .venv/bin/python Debug/test_intraday_poll.py
"""

import os
import sys

_DEBUG_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_DEBUG_DIR)
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, _DEBUG_DIR)

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from DataAPI.KLineStore import KLineStore
from DataAPI.RecomputeCursor import MemoryCursor
from KLine.KLine_Unit import CKLine_Unit

import intraday_poll as ip


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def mklu(y, mo, d, h, mi, o, c):
    hi = max(o, c) + 0.1
    lo = min(o, c) - 0.1
    return CKLine_Unit({
        DATA_FIELD.FIELD_TIME: CTime(y, mo, d, h, mi, 0, auto=False),
        DATA_FIELD.FIELD_OPEN: o,
        DATA_FIELD.FIELD_HIGH: hi,
        DATA_FIELD.FIELD_LOW: lo,
        DATA_FIELD.FIELD_CLOSE: c,
        DATA_FIELD.FIELD_VOLUME: 1000.0,
    })


class FakeMinute:
    """伪分钟源：按 code 返回固定 bar，指定 code 可注入失败。"""
    FAIL_CODES = set()
    BARS = {}

    def __init__(self, code, k_type=None, begin_date=None, end_date=None, autype=None):
        self.code = code

    def get_kl_data(self):
        if self.code in self.FAIL_CODES:
            raise RuntimeError(f"fake failure for {self.code}")
        yield from self.BARS.get(self.code, [])


class SpyCursor:
    """包装 MemoryCursor，记录 recompute 调用序列。"""

    def __init__(self):
        self._inner = MemoryCursor()
        self.recompute_calls = []

    def get(self, code, kl_type, autype):
        return self._inner.get(code, kl_type, autype)

    def set(self, code, kl_type, autype, time_key):
        self._inner.set(code, kl_type, autype, time_key)


def spy_recompute(calls):
    def fn(code, k_type, autype):
        calls.append((code, k_type.name, autype.name))
    return fn


PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ok - {name}")


# ---------------------------------------------------------------------------
# 5.2 已收盘 bar 判定
# ---------------------------------------------------------------------------
def test_filter_closed_bars():
    import pandas as pd

    print("[5.2] filter_closed_bars / is_in_session")
    df = pd.DataFrame({"time_key": [
        "2026-09-07 09:30:00", "2026-09-07 09:35:00",
        "2026-09-07 09:40:00", "2026-09-07 09:45:00",
    ]})
    closed = ip.filter_closed_bars(df, "2026-09-07 09:37:00")
    check("形成中的 bar（09:40/09:45）被排除", len(closed) == 2)

    sessions = [["09:30", "11:30"], ["13:00", "15:00"]]
    check("盘中 10:00 在交易时段", ip.is_in_session(datetime(2026, 9, 7, 10, 0), sessions))
    check("午休 12:00 不在交易时段", not ip.is_in_session(datetime(2026, 9, 7, 12, 0), sessions))


def test_poll_once_only_closed():
    print("[5.2] poll_once 只落已收盘 bar")
    FakeMinute.BARS["sz.000001"] = [
        mklu(2026, 9, 7, 9, 30, 10.0, 10.1),  # 已收盘
        mklu(2026, 9, 7, 9, 35, 10.1, 10.2),  # 已收盘
        mklu(2026, 9, 7, 9, 40, 10.2, 10.3),  # 形成中
        mklu(2026, 9, 7, 9, 45, 10.3, 10.4),  # 形成中
    ]
    with KLineStore(":memory:") as store:
        wm = ip.poll_once(FakeMinute, "sz.000001", KL_TYPE.K_5M, __import__("Common.CEnum", fromlist=["AUTYPE"]).AUTYPE.QFQ,
                          store, "2026-09-07 09:37:00")
        check("水位 = 最后一根已收盘 bar 09:35", wm == "2026-09-07 09:35:00")
        df = store.query("sz.000001", "K_5M", "QFQ")
        check("库中仅 2 行（形成中 bar 未落库）", len(df) == 2)


# ---------------------------------------------------------------------------
# 5.3 水位通知 + 游标落独立存储（非 DuckDB）
# ---------------------------------------------------------------------------
def test_recompute_and_cursor():
    print("[5.3] 新 bar 触发重算，游标落独立 cursor")
    FakeMinute.FAIL_CODES = set()
    FakeMinute.BARS["sz.000001"] = [
        mklu(2026, 9, 7, 9, 30, 10.0, 10.1),
        mklu(2026, 9, 7, 9, 35, 10.1, 10.2),
    ]
    cfg = {"stocks": [{"code": "sz.000001", "kl_types": ["K_5M"], "autypes": ["QFQ"]}]}
    calls = []
    cursor = SpyCursor()
    rec = spy_recompute(calls)

    with KLineStore(":memory:") as store:
        # 第一轮：新 bar 落库 → 触发重算 → 游标推进
        ip.run_once(cfg, store, FakeMinute, cursor, rec, "2026-09-07 09:37:00")
        check("首轮触发 1 次重算", len(calls) == 1)
        check("游标推进到 09:35", cursor.get("sz.000001", "K_5M", "QFQ") == "2026-09-07 09:35:00")

        # 第二轮：无新 bar → 不重复重算、游标不动
        calls.clear()
        ip.run_once(cfg, store, FakeMinute, cursor, rec, "2026-09-07 09:38:00")
        check("无新 bar 不重复重算", len(calls) == 0)
        check("游标保持不变", cursor.get("sz.000001", "K_5M", "QFQ") == "2026-09-07 09:35:00")

        # 游标不落 DuckDB：kline 库中不存在 recompute_cursor 表
        tables = [r[0] for r in store._conn.execute(
            "SELECT table_name FROM information_schema.tables").fetchall()]
        check("DuckDB 无 recompute_cursor 表（游标在独立 PG/内存）", "recompute_cursor" not in tables)


# ---------------------------------------------------------------------------
# 5.4 失败隔离 + 指数退避
# ---------------------------------------------------------------------------
def test_failure_isolation_and_backoff():
    print("[5.4] 单股失败隔离 + 指数退避")
    FakeMinute.FAIL_CODES = {"sz.000002"}  # 000002 注入失败
    FakeMinute.BARS["sz.000001"] = [mklu(2026, 9, 7, 9, 30, 10.0, 10.1)]
    FakeMinute.BARS["sz.000002"] = [mklu(2026, 9, 7, 9, 30, 20.0, 20.1)]
    cfg = {"stocks": [
        {"code": "sz.000001", "kl_types": ["K_5M"], "autypes": ["QFQ"]},
        {"code": "sz.000002", "kl_types": ["K_5M"], "autypes": ["QFQ"]},
    ]}
    calls = []
    cursor = SpyCursor()
    rec = spy_recompute(calls)

    with KLineStore(":memory:") as store:
        backoff = ip.run_once(cfg, store, FakeMinute, cursor, rec, "2026-09-07 09:37:00")
        # 000001 成功
        check("成功股 000001 触发重算", ("sz.000001", "K_5M", "QFQ") in calls)
        # 000002 失败 → 进入退避
        key = ("sz.000002", "K_5M", "QFQ")
        check("失败股 000002 进入退避", key in backoff and backoff[key]["failures"] == 1)

        # 立即第二轮：000002 仍在退避窗口 → 被跳过；000001 无新 bar → 不重算
        calls.clear()
        backoff = ip.run_once(cfg, store, FakeMinute, cursor, rec, "2026-09-07 09:38:00", backoff=backoff)
        check("退避窗口内失败股被跳过（不再抛错）", key in backoff and backoff[key]["failures"] == 1)
        check("第二轮成功股无新 bar 不重算", len(calls) == 0)


def test_iter_intraday_jobs_filters():
    print("[5.2] iter_intraday_jobs 只取分钟级")
    cfg = {"stocks": [{"code": "sz.000001", "kl_types": ["K_5M", "K_DAY"], "autypes": ["QFQ"]}]}
    jobs = list(ip.iter_intraday_jobs(cfg))
    check("日线被过滤，仅保留 K_5M", [j[1] for j in jobs] == [KL_TYPE.K_5M])


def test_run_loop_skips_offsession():
    print("[5.2] run_loop 交易时段门控 + 迭代上限")
    FakeMinute.FAIL_CODES = set()
    FakeMinute.BARS["sz.000001"] = [mklu(2026, 9, 7, 9, 30, 10.0, 10.1)]
    cfg = {"stocks": [{"code": "sz.000001", "kl_types": ["K_5M"], "autypes": ["QFQ"]}]}
    calls = []
    cursor = SpyCursor()
    rec = spy_recompute(calls)
    slept = []
    # 设定一个当前真实时间必然不在的时段，验证非交易时段跳过 run_once
    ip.run_loop(cfg, KLineStore(":memory:"), FakeMinute, cursor, rec,
                sessions=[["00:00", "00:01"]], max_iterations=3, sleep_fn=lambda s: slept.append(s))
    check("非交易时段不触发重算", len(calls) == 0)
    # 3 次迭代之间 sleep 2 次（末次迭代命中上限直接 break）
    check("循环按迭代上限退出且 sleep 被调用", len(slept) == 2)


from datetime import datetime  # noqa: E402  (用于 is_in_session 测试)


def main():
    global PASS
    PASS = 0
    test_filter_closed_bars()
    test_poll_once_only_closed()
    test_recompute_and_cursor()
    test_failure_isolation_and_backoff()
    test_iter_intraday_jobs_filters()
    test_run_loop_skips_offsession()
    print(f"\nall {PASS} checks passed")


if __name__ == "__main__":
    main()
