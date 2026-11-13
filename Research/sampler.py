"""逐步回放 ClickHouse 日线，只在分型第三元素确认时冻结买点。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.ChanException import CChanException
from Research.config import FEATURE_COLUMNS, make_chan_config
from Research.features import build_feature_row, new_volume_window, push_volume
from Research.labels import PendingBuy


IDENTITY_COLUMNS = (
    "code",
    "decision_time",
    "decision_idx",
    "bsp_klu_idx",
    "decision_price",
    "bsp_types",
    "is_strict_t1",
    "multi_bi_zs_cnt",
    "zs_width",
    "zs_upper_fallback",
    "bsp_persisted",
)

OUTCOME_COLUMNS = (
    "obs_bars",
    "complete_10",
    "label_10",
    "barrier_reason_10",
    "exit_reason_10",
    "exit_time_10",
    "exit_price_10",
    "net_return_10",
    "forward_return_10",
    "mfe_10",
    "mae_10",
    "horizon_end_10",
    "path_10",
    "complete_20",
    "label_20",
    "barrier_reason_20",
    "exit_reason_20",
    "exit_time_20",
    "exit_price_20",
    "net_return_20",
    "forward_return_20",
    "mfe_20",
    "mae_20",
    "horizon_end_20",
    "path_20",
    "label_zs_10",
    "barrier_zs_reason_10",
)

EVENT_COLUMNS = IDENTITY_COLUMNS + OUTCOME_COLUMNS + tuple(FEATURE_COLUMNS)


@dataclass
class TrackedBuy:
    decision_idx: int
    bsp_klu_idx: int
    pending: PendingBuy
    base: dict = field(default_factory=dict)


def _decision_klu(chan: CChan):
    kl = chan[0]
    if len(kl) < 1 or len(kl[-1]) == 0:
        return None
    return kl[-1][-1]


def confirmed_bsp(chan: CChan):
    """最新买卖点落在倒数第二根合并 K 上，分型第三元素刚刚出现。"""
    kl = chan[0]
    if len(kl) < 2:
        return None
    bsp_list = chan.get_latest_bsp()
    if not bsp_list:
        return None
    last = bsp_list[0]
    if last.klu.klc.idx != kl[-2].idx:
        return None
    return last


def sample_code(code: str, begin: str, end: str | None) -> list[dict]:
    """单标的逐步采样。买卖点后来被改写，不会回写已经冻结的特征。"""
    config = make_chan_config()
    chan = CChan(
        code=code,
        begin_time=begin,
        end_time=end,
        data_src=DATA_SRC.QAClickhouse,
        lv_list=[KL_TYPE.K_DAY],
        config=config,
        autype=AUTYPE.QFQ,
    )
    volumes = new_volume_window()
    seen: set[int] = set()
    tracked: list[TrackedBuy] = []

    for snapshot in chan.step_load():
        last_klu = _decision_klu(snapshot)
        if last_klu is None:
            continue
        push_volume(volumes, last_klu)
        point = confirmed_bsp(snapshot)
        sell_price = None
        if point is not None and point.klu.idx not in seen and not point.is_buy:
            sell_price = float(last_klu.close)
        bar_time = last_klu.time.toDateStr("-")
        for item in tracked:
            if last_klu.idx > item.decision_idx:
                item.pending.add_bar(
                    bar_time,
                    float(last_klu.high),
                    float(last_klu.low),
                    float(last_klu.close),
                    sell_price=sell_price,
                )
        if point is None or point.klu.idx in seen:
            continue
        seen.add(point.klu.idx)
        if not point.is_buy:
            continue
        feature_row, aux = build_feature_row(point, last_klu, snapshot, volumes)
        upper_zs, zs_fallback = aux["upper_zs"]
        pending = PendingBuy(entry=float(last_klu.close), upper_zs=upper_zs)
        tracked.append(TrackedBuy(
            decision_idx=last_klu.idx,
            bsp_klu_idx=point.klu.idx,
            pending=pending,
            base={
                "code": code,
                "decision_time": bar_time,
                "decision_idx": last_klu.idx,
                "bsp_klu_idx": point.klu.idx,
                "decision_price": float(last_klu.close),
                "bsp_types": aux["bsp_types"],
                "is_strict_t1": aux["is_strict_t1"],
                "multi_bi_zs_cnt": aux["multi_bi_zs_cnt"],
                "zs_width": aux["zs_width"],
                "zs_upper_fallback": zs_fallback,
                **feature_row,
            },
        ))

    final_buy_ids = {bsp.klu.idx for bsp in chan.get_latest_bsp(number=0) if bsp.is_buy}
    rows = []
    for item in tracked:
        row = dict(item.base)
        row.update(item.pending.outcome())
        # 诊断列：全历史结束后该点是否还在。不进入模型特征。
        row["bsp_persisted"] = int(item.bsp_klu_idx in final_buy_ids)
        rows.append(row)
    return rows


def _write_events(rows: list[dict], out_path: str) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in EVENT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame.loc[:, list(EVENT_COLUMNS)]
    frame.to_csv(out_path, index=False)
    return frame


def sample_codes(codes: list[str], begin: str, end: str | None, out_path: str) -> pd.DataFrame:
    rows: list[dict] = []
    total = len(codes)
    for index, code in enumerate(codes, start=1):
        try:
            got = sample_code(code, begin, end)
        except CChanException as exc:
            print(f"[skip] {code}: {exc.msg}")
            continue
        except Exception as exc:
            print(f"[skip] {code}: {type(exc).__name__}: {exc}")
            continue
        print(f"[sample] {index}/{total} {code}: buy={len(got)}")
        rows.extend(got)
        if index % 10 == 0 or index == total:
            _write_events(rows, out_path)
            print(f"[sample] checkpoint {index}/{total} rows={len(rows)}")
    frame = _write_events(rows, out_path)
    print(f"[sample] wrote {len(frame)} rows -> {out_path}")
    return frame
