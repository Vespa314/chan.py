"""用 feature.meta 的列顺序打分。step_load 与 trigger_load 共用同一个确认门控。"""

from __future__ import annotations

import json
from pathlib import Path

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.QAClickhouseAPI import CQAClickhouse
from Research.config import make_chan_config
from Research.features import build_feature_row, new_volume_window, push_volume, vectorize
from Research.sampler import _decision_klu, confirmed_bsp


def load_columns(meta_path: str) -> list[str]:
    payload = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return list(payload["columns"])
    return list(payload)


def score_row(model, features: dict, columns: list[str]) -> float:
    import xgboost as xgb

    matrix = xgb.DMatrix([vectorize(features, columns)], feature_names=columns)
    return float(model.predict(matrix)[0])


def score_snapshot(chan: CChan, seen: set[int], volumes, model, columns: list[str]):
    """确认时刻打分。卖点只登记，不打分。"""
    last_klu = _decision_klu(chan)
    if last_klu is None:
        return None
    push_volume(volumes, last_klu)
    point = confirmed_bsp(chan)
    if point is None or point.klu.idx in seen:
        return None
    seen.add(point.klu.idx)
    if not point.is_buy:
        return None
    feature_row, _aux = build_feature_row(point, last_klu, chan, volumes)
    return {
        "time": last_klu.time.toDateStr("-"),
        "bsp_klu_idx": point.klu.idx,
        "score": score_row(model, feature_row, columns),
        "features": feature_row,
    }


def replay_trigger_load(code: str, begin: str, end: str | None, model, columns: list[str]) -> list[dict]:
    """外部逐根喂 K，和实盘 trigger_load 同一条路径。"""
    CQAClickhouse.do_init()
    try:
        api = CQAClickhouse(code=code, k_type=KL_TYPE.K_DAY, begin_date=begin, end_date=end, autype=AUTYPE.QFQ)
        chan = CChan(
            code=code,
            begin_time=begin,
            end_time=end,
            data_src=DATA_SRC.QAClickhouse,
            lv_list=[KL_TYPE.K_DAY],
            config=make_chan_config(),
            autype=AUTYPE.QFQ,
        )
        seen: set[int] = set()
        volumes = new_volume_window()
        scored = []
        for klu in api.get_kl_data():
            chan.trigger_load({KL_TYPE.K_DAY: [klu]})
            hit = score_snapshot(chan, seen, volumes, model, columns)
            if hit is not None:
                scored.append(hit)
        return scored
    finally:
        CQAClickhouse.do_close()
