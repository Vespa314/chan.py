"""按决策日和标签结束日切分。标签用到的 K 线不得进入下一段。"""

from __future__ import annotations

from Research.config import EMBARGO_DAYS, FOLDS


def _as_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text


def _complete(row, horizon: int = 10) -> bool:
    try:
        return int(float(row[f"complete_{horizon}"])) == 1
    except (TypeError, ValueError, KeyError):
        return False


def horizon_end_before(row, boundary: str, horizon: int = EMBARGO_DAYS) -> bool:
    """标签窗口的最后一天早于下一段起点。没有凑满窗口的样本不进训练或验证。"""
    end = _as_text(row.get(f"horizon_end_{horizon}"))
    return bool(end) and end < boundary


def select_train(row, fold: dict) -> bool:
    decision = _as_text(row.get("decision_time"))
    return (
        _complete(row, 10)
        and fold["train_start"] <= decision <= fold["train_end"]
        and horizon_end_before(row, fold["val_start"])
    )


def select_val(row, fold: dict) -> bool:
    decision = _as_text(row.get("decision_time"))
    return (
        _complete(row, 10)
        and fold["val_start"] <= decision <= fold["val_end"]
        and horizon_end_before(row, fold["test_start"])
    )


def select_test(row, fold: dict) -> bool:
    decision = _as_text(row.get("decision_time"))
    return _complete(row, 10) and fold["test_start"] <= decision <= fold["test_end"]


def iter_folds():
    yield from FOLDS
