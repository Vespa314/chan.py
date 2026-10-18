"""无模型对照：全部确认买点，以及严格一类买点。"""

from __future__ import annotations

import math

from Research.portfolio import simulate


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _complete_records(records, ret_col: str = "net_return_10") -> list[dict]:
    kept = []
    for record in records:
        try:
            complete = int(float(record.get("complete_10", 0))) == 1
        except (TypeError, ValueError):
            complete = False
        if complete and _finite(record.get(ret_col)):
            kept.append(record)
    return kept


def event_stats(records, ret_col: str = "net_return_10") -> dict:
    values = [float(record[ret_col]) for record in records]
    if not values:
        return {"n": 0, "mean_net_return": None, "win_rate": None}
    wins = sum(value > 0 for value in values)
    return {
        "n": len(values),
        "mean_net_return": sum(values) / len(values),
        "win_rate": wins / len(values),
    }


def _book(records, ret_col: str) -> dict:
    stats = event_stats(records, ret_col)
    account = simulate(records, ret_col=ret_col, exit_col="exit_time_10", path_col="path_10")
    stats["final_equity"] = account["final_equity"]
    stats["max_drawdown"] = account["max_drawdown"]
    stats["n_trades"] = account["n_trades"]
    stats["curve"] = account["curve"]
    return stats


def summarize(records, ret_col: str = "net_return_10") -> dict:
    """两条基线共用同一批确认买点。严格一类是其中背驰和中枢达标的子集。"""
    complete = _complete_records(records, ret_col)
    strict = []
    for record in complete:
        try:
            flag = int(float(record.get("is_strict_t1", 0))) == 1
        except (TypeError, ValueError):
            flag = False
        if flag:
            strict.append(record)
    return {
        "all_buys": _book(complete, ret_col),
        "strict_type1": _book(strict, ret_col),
    }
