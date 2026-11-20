"""等权、最多 10 只的研究组合。收益在出场日按事件净收益入账。"""

from __future__ import annotations

import math
from collections import defaultdict

from Research.config import MAX_POSITIONS, SIDE_COST


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text


def parse_path(text) -> dict[str, float]:
    path = {}
    raw = _text(text)
    if not raw:
        return path
    for part in raw.split("|"):
        if ":" not in part:
            continue
        date, close = part.split(":", 1)
        if _finite(close):
            path[date] = float(close)
    return path


def _prepare(records, ret_col: str, exit_col: str, path_col: str, score_col: str | None, threshold: float | None) -> list[dict]:
    prepared = []
    for record in records:
        if not _finite(record.get(ret_col)) or not _finite(record.get("decision_price")):
            continue
        exit_time = _text(record.get(exit_col))
        decision_time = _text(record.get("decision_time"))
        if not exit_time or not decision_time:
            continue
        if score_col is not None and threshold is not None:
            if not _finite(record.get(score_col)) or float(record[score_col]) < threshold:
                continue
        prepared.append({
            "code": _text(record.get("code")),
            "decision_time": decision_time,
            "exit_time": exit_time,
            "entry": float(record["decision_price"]),
            "net_return": float(record[ret_col]),
            "path": parse_path(record.get(path_col)),
            "score": float(record[score_col]) if score_col and _finite(record.get(score_col)) else 0.0,
        })
    prepared.sort(key=lambda item: (item["decision_time"], -item["score"], item["code"]))
    return prepared


def max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst


def simulate(
    records,
    ret_col: str = "net_return_10",
    exit_col: str = "exit_time_10",
    path_col: str = "path_10",
    score_col: str | None = None,
    threshold: float | None = None,
    max_positions: int = MAX_POSITIONS,
    side_cost: float = SIDE_COST,
) -> dict:
    """持仓按当日收盘盯市，出场日改用已经扣费的事件净收益，避免和事件收益对不上。"""
    events = _prepare(records, ret_col, exit_col, path_col, score_col, threshold)
    if not events:
        return {"n_trades": 0, "final_equity": 1.0, "max_drawdown": 0.0, "curve": []}

    by_entry: dict[str, list[dict]] = defaultdict(list)
    dates = set()
    for event in events:
        by_entry[event["decision_time"]].append(event)
        dates.add(event["decision_time"])
        dates.add(event["exit_time"])
        dates.update(event["path"])
    calendar = sorted(dates)

    cash = 1.0
    positions: list[dict] = []
    curve = []
    opened = 0
    cost_factor = 1.0 - 2.0 * side_cost

    def mark(position: dict, date: str) -> float:
        if date == position["decision_time"] or position["entry"] == 0:
            price = position["entry"]
        else:
            price = position["path"].get(date, position["entry"])
        return position["alloc"] * (price / position["entry"]) * cost_factor

    for date in calendar:
        staying = []
        for position in positions:
            if position["exit_time"] == date:
                cash += position["alloc"] * (1.0 + position["net_return"])
            else:
                staying.append(position)
        positions = staying

        equity_now = cash + sum(mark(position, date) for position in positions)
        todays = by_entry.get(date, [])
        held = {position["code"] for position in positions}
        for event in todays:
            if len(positions) >= max_positions or event["code"] in held:
                continue
            alloc = equity_now / max_positions
            if alloc > cash:
                alloc = cash
            if alloc <= 1e-12:
                break
            cash -= alloc
            positions.append({
                "code": event["code"],
                "alloc": alloc,
                "entry": event["entry"],
                "decision_time": event["decision_time"],
                "exit_time": event["exit_time"],
                "net_return": event["net_return"],
                "path": event["path"],
            })
            held.add(event["code"])
            opened += 1

        equity = cash + sum(mark(position, date) for position in positions)
        curve.append({"date": date, "equity": equity})

    return {
        "n_trades": opened,
        "final_equity": curve[-1]["equity"] if curve else 1.0,
        "max_drawdown": max_drawdown([point["equity"] for point in curve]),
        "curve": curve,
    }
