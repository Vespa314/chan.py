# -*- coding: utf-8 -*-
"""
灌数公共工具 - CKLine_Unit 与 DataFrame 行之间的转换、数据校验、交易日历。

日线灌数脚本（Debug/download_kl.py）与盘中轮询引擎（Debug/intraday_poll.py）
共用这里的转换/校验逻辑，避免重复实现。
"""

import json
import logging

import pandas as pd

from Common.CEnum import AUTYPE, KL_TYPE
from .KLineStore import ctime_to_str

log = logging.getLogger("ingest")

EARLIEST = "1990-12-19"           # A 股最早交易日附近，作为首次全量回填的起始
LOOKBACK_SESSIONS = 3             # 增量续拉的回看交易日数（自愈窗口）
JUMP_THRESHOLD = 0.20             # 单根涨跌幅告警阈值（可配，仅告警不拒绝）
DEFAULT_STALE_HOURS = {"intraday": 0.5, "day": 48.0}  # 停更告警阈值（小时）


def parse_kl_type(s: str) -> KL_TYPE:
    return KL_TYPE[s.upper()]


def parse_autype(s: str) -> AUTYPE:
    return AUTYPE[s.upper()]


def klu_to_row(klu, code: str, k_type: KL_TYPE, autype: AUTYPE) -> dict:
    """把一根 CKLine_Unit 转成 kline 表的一行（缺交易信息的列留空，由 upsert 补 NULL）。"""
    d = {
        "code": code,
        "kl_type": k_type.name,
        "autype": autype.name,
        "time_key": ctime_to_str(klu.time),
        "open": klu.open,
        "high": klu.high,
        "low": klu.low,
        "close": klu.close,
    }
    # trade_info.metric 键为 "volume"/"turnover"/"turnover_rate"，与表列名一致
    for k, v in klu.trade_info.metric.items():
        if v is not None:
            d[k] = v
    return d


def validate(df: pd.DataFrame):
    """结构化校验 + 跳变告警。

    返回 (valid_df, rejected_count, warnings)。
    - 拒绝：OHLC 关系非法（high < max(open,close)、low > min(open,close)、
      high < low、价格非负不满足）；时间乱序（time_key 相对运行最大值回退）。
    - 告警但保留：单根涨跌幅超阈值（如除权除息导致的真实跳空）。
    """
    warnings = []

    bad = (
        (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
        | (df["high"] < df["low"])
        | ((df[["open", "high", "low", "close"]] < 0).any(axis=1))
    )
    rejected = int(bad.sum())
    valid = df[~bad].reset_index(drop=True)

    # 时间乱序：任何 time_key < 已见最大值的行视为乱序拒绝；重复（相等）交给 upsert 去重
    drop_idx = []
    cur_max = None
    for i, t in enumerate(valid["time_key"]):
        if cur_max is not None and t < cur_max:
            drop_idx.append(i)
        else:
            cur_max = t
    if drop_idx:
        warnings.append(f"时间乱序 {len(drop_idx)} 行被拒绝")
        valid = valid.drop(index=drop_idx).reset_index(drop=True)
        rejected += len(drop_idx)

    # 异常跳变告警（保留）
    prev_close = None
    for t, c in zip(valid["time_key"], valid["close"]):
        if prev_close is not None and prev_close > 0:
            pct = abs(c / prev_close - 1)
            if pct > JUMP_THRESHOLD:
                warnings.append(f"异常跳变 {t}: {pct:.2%}（保留，疑似除权除息）")
        prev_close = c

    return valid, rejected, warnings


def get_calendar():
    """返回 A 股交易日历（exchange_calendars），不可用时返回 None。"""
    try:
        import exchange_calendars as xcals
        return xcals.get_calendar("XSHG")
    except Exception as e:
        log.warning("交易日历不可用：%s", e)
        return None


def load_config(path: str) -> dict:
    """读取 JSON 配置文件（schema 见 Debug/ingest_config.example.json）。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_ingest_jobs(cfg: dict):
    """按配置文件展开为 (code, KL_TYPE, AUTYPE) 三元组，供批量灌数/状态遍历。"""
    defaults = cfg.get("defaults", {})
    default_autype = defaults.get("autype", "QFQ")
    for s in cfg.get("stocks", []):
        code = s["code"]
        for kt in s.get("kl_types", ["K_DAY"]):
            for au in s.get("autypes", [default_autype]):
                yield code, parse_kl_type(kt), parse_autype(au)
