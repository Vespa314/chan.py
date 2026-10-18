"""决策当时可见的特征。类型相关字段缺失时写 0，并带 _missing，不用哨兵值。"""

from __future__ import annotations

import math
from collections import deque

from Common.ChanException import CChanException
from Research.config import (
    CONFIRM_OPTIONAL,
    ENGINE_OPTIONAL,
    FEATURE_COLUMNS,
    STRICT_DIVERGENCE,
    STRICT_MIN_ZS,
    STRUCTURE_OPTIONAL,
    TYPE_COLUMNS,
    TYPE_VALUE_TO_COLUMN,
    VOLUME_WINDOW,
    ZS_UPPER_MULT,
)


def is_finite_number(value) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def apply_schema(values: dict) -> dict[str, float]:
    """把参差不齐的原始字段收成固定列。训练和推理都走这里。"""
    row: dict[str, float] = {}
    row["is_buy"] = 1.0 if is_finite_number(values.get("is_buy")) and float(values["is_buy"]) != 0 else 0.0
    for column in TYPE_COLUMNS:
        raw = values.get(column)
        row[column] = 1.0 if is_finite_number(raw) and float(raw) != 0 else 0.0
    row["bsp_bi_amp"] = float(values["bsp_bi_amp"]) if is_finite_number(values.get("bsp_bi_amp")) else 0.0
    row["bi_is_sure"] = 1.0 if is_finite_number(values.get("bi_is_sure")) and float(values["bi_is_sure"]) != 0 else 0.0
    for name in ENGINE_OPTIONAL + STRUCTURE_OPTIONAL + CONFIRM_OPTIONAL:
        raw = values.get(name)
        if is_finite_number(raw):
            row[name] = float(raw)
            row[f"{name}_missing"] = 0.0
        else:
            row[name] = 0.0
            row[f"{name}_missing"] = 1.0
    return {column: row[column] for column in FEATURE_COLUMNS}


def vectorize(features: dict, columns: list[str]) -> list[float]:
    """按 feature.meta 的列顺序取值。meta 里有、当前行没有的列填 0。"""
    return [float(features[name]) if name in features and is_finite_number(features[name]) else 0.0 for name in columns]


def klu_volume(klu) -> float | None:
    trade_info = getattr(klu, "trade_info", None)
    metric = getattr(trade_info, "metric", None)
    if not metric:
        return None
    volume = metric.get("volume")
    if not is_finite_number(volume):
        return None
    return float(volume)


def push_volume(window: deque, klu) -> None:
    volume = klu_volume(klu)
    if volume is not None:
        window.append(volume)


def is_strict_type1(type_values: set[str], divergence_rate, multi_bi_zs_cnt: int) -> bool:
    """对应 demo1：一类或盘整一类，背驰比不超过 0.8，且至少有一个多笔中枢。"""
    if not ({"1", "1p"} & type_values):
        return False
    if not is_finite_number(divergence_rate) or float(divergence_rate) > STRICT_DIVERGENCE:
        return False
    return multi_bi_zs_cnt >= STRICT_MIN_ZS


def _engine_values(bsp) -> dict:
    values = {}
    for name, raw in bsp.features.items():
        if is_finite_number(raw):
            values[name] = float(raw)
    return values


def _structure_values(bsp, chan, decision_close: float) -> tuple[dict, int, float | None]:
    """只读笔、线段、中枢。返回结构特征、多笔中枢个数、中枢相对高度。"""
    values: dict = {"bi_is_sure": 1.0 if bsp.bi.is_sure else 0.0}
    multi_bi_zs_cnt = 0
    zs_width = None
    seg = getattr(bsp.bi, "parent_seg", None)
    if seg is not None:
        try:
            values["seg_bi_cnt"] = float(len(seg.bi_list))
            values["seg_amp"] = float(seg.amp())
            values["seg_is_down"] = 1.0 if seg.is_down() else 0.0
            multi_bi_zs_cnt = int(seg.get_multi_bi_zs_cnt())
            zs_list = seg.get_multi_bi_zs_lst()
        except (AssertionError, AttributeError, IndexError, ZeroDivisionError, TypeError, ValueError, CChanException):
            zs_list = []
        if zs_list:
            zs = zs_list[-1]
            if is_finite_number(zs.low) and float(zs.low) > 0 and is_finite_number(zs.high):
                zs_width = (float(zs.high) - float(zs.low)) / float(zs.low)
                values["zs_width"] = zs_width
                if decision_close > float(zs.high):
                    values["price_vs_zs"] = 1.0
                elif decision_close < float(zs.low):
                    values["price_vs_zs"] = -1.0
                else:
                    values["price_vs_zs"] = 0.0
    if bsp.bi.idx >= 2:
        try:
            prev = chan[0].bi_list[bsp.bi.idx - 2]
            prev_amp = float(prev.amp())
            if prev_amp > 1e-12:
                values["bi_amp_ratio"] = float(bsp.bi.amp()) / prev_amp
        except (AssertionError, AttributeError, IndexError, ZeroDivisionError, TypeError, ValueError, CChanException):
            pass
    return values, multi_bi_zs_cnt, zs_width


def _confirm_values(klu, volumes: deque) -> dict:
    values = {}
    open_px = float(klu.open)
    close_px = float(klu.close)
    high_px = float(klu.high)
    low_px = float(klu.low)
    if open_px != 0:
        values["open_klu_rate"] = (close_px - open_px) / open_px
    amplitude = high_px - low_px
    if amplitude > 0:
        values["body_ratio"] = abs(close_px - open_px) / amplitude
    macd = getattr(klu, "macd", None)
    if macd is not None and is_finite_number(getattr(macd, "macd", None)):
        values["macd_hist"] = float(macd.macd)
    rsi = getattr(klu, "rsi", None)
    if is_finite_number(rsi):
        values["rsi"] = float(rsi)
    boll = getattr(klu, "boll", None)
    if boll is not None and is_finite_number(boll.UP) and is_finite_number(boll.DOWN) and float(boll.UP) != float(boll.DOWN):
        values["boll_pos"] = (close_px - float(boll.DOWN)) / (float(boll.UP) - float(boll.DOWN))
    if volumes:
        mean_volume = sum(volumes) / len(volumes)
        current = volumes[-1]
        if mean_volume > 0:
            values["vol_ratio"] = current / mean_volume
    return values


def build_feature_row(bsp, last_klu, chan, volumes: deque) -> tuple[dict[str, float], dict]:
    """在确认时刻写入策略特征并立刻复制。返回模型行，以及标签要用的辅助字段。"""
    confirm = _confirm_values(last_klu, volumes)
    # 与 demo5 一样把确认 K 线特征挂到买卖点上，随后马上复制走。
    bsp.add_feat({name: value for name, value in confirm.items() if is_finite_number(value)})
    raw = _engine_values(bsp)
    structure, multi_bi_zs_cnt, zs_width = _structure_values(bsp, chan, float(last_klu.close))
    type_values = {bsp_type.value for bsp_type in bsp.type}
    merged = {
        "is_buy": 1.0 if bsp.is_buy else 0.0,
        **{column: 0.0 for column in TYPE_COLUMNS},
        **raw,
        **structure,
        **confirm,
    }
    for type_value in type_values:
        column = TYPE_VALUE_TO_COLUMN.get(type_value)
        if column is not None:
            merged[column] = 1.0
    row = apply_schema(merged)
    aux = {
        "bsp_types": "|".join(sorted(type_values, key=lambda item: list(TYPE_VALUE_TO_COLUMN).index(item))),
        "multi_bi_zs_cnt": multi_bi_zs_cnt,
        "is_strict_t1": int(is_strict_type1(type_values, raw.get("divergence_rate"), multi_bi_zs_cnt)),
        "zs_width": zs_width,
        "upper_zs": upper_from_zs(zs_width),
    }
    return row, aux


def upper_from_zs(zs_width: float | None) -> tuple[float, int]:
    """中枢相对高度的 2 倍。没有中枢时退回 8%，并打上 fallback 标记。"""
    from Research.config import UPPER_RETURN

    if zs_width is None or not is_finite_number(zs_width) or float(zs_width) <= 0:
        return UPPER_RETURN, 1
    return ZS_UPPER_MULT * float(zs_width), 0


def new_volume_window() -> deque:
    return deque(maxlen=VOLUME_WINDOW)
