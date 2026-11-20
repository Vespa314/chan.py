"""时间滚动训练。阈值在验证段按扣费收益选择，再拿到下一段样本外比较。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from Research.baseline import event_stats, summarize
from Research.config import (
    FEATURE_COLUMNS,
    MIN_THRESHOLD_EVENTS,
    THRESHOLDS,
    XGB_ETA,
    XGB_MAX_DEPTH,
    XGB_ROUNDS,
)
from Research.portfolio import simulate
from Research.split import iter_folds, select_test, select_train, select_val


def load_events(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _records(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _subset(frame: pd.DataFrame, predicate) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    flags = [i for i, record in enumerate(frame.to_dict(orient="records")) if predicate(record)]
    return frame.iloc[flags].copy()


def choose_threshold(records, min_count: int | None = None) -> dict | None:
    """验证段上让扣费后平均收益最高的概率阈值。样本不够则不选。"""
    usable = []
    for record in records:
        try:
            score = float(record["score"])
            ret = float(record["net_return_10"])
        except (TypeError, ValueError, KeyError):
            continue
        if score == score and ret == ret:
            usable.append((score, ret))
    if not usable:
        return None
    if min_count is None:
        if len(usable) < MIN_THRESHOLD_EVENTS:
            min_count = max(1, len(usable) // 5) if len(usable) >= 5 else len(usable)
        else:
            min_count = MIN_THRESHOLD_EVENTS
    best = None
    for threshold in THRESHOLDS:
        chosen = [ret for score, ret in usable if score >= threshold]
        if len(chosen) < min_count:
            continue
        mean = sum(chosen) / len(chosen)
        if best is None or mean > best["mean_net_return"] + 1e-12 or (
            abs(mean - best["mean_net_return"]) <= 1e-12 and threshold > best["threshold"]
        ):
            best = {
                "threshold": threshold,
                "mean_net_return": mean,
                "n": len(chosen),
                "min_count": min_count,
            }
    return best


def _fit(train_frame: pd.DataFrame):
    import xgboost as xgb

    labels = train_frame["label_10"].astype(float)
    positive = int((labels == 1).sum())
    negative = int((labels == 0).sum())
    if positive == 0 or negative == 0:
        raise ValueError("训练集只有一个类别，跳过该折")
    params = {
        "max_depth": XGB_MAX_DEPTH,
        "eta": XGB_ETA,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "scale_pos_weight": negative / positive,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "seed": 7,
        "verbosity": 0,
    }
    dataset = xgb.DMatrix(train_frame.loc[:, FEATURE_COLUMNS], label=labels, feature_names=FEATURE_COLUMNS)
    return xgb.train(params, dataset, num_boost_round=XGB_ROUNDS)


def _predict(model, frame: pd.DataFrame) -> list[float]:
    import xgboost as xgb

    if frame.empty:
        return []
    dataset = xgb.DMatrix(frame.loc[:, FEATURE_COLUMNS], feature_names=FEATURE_COLUMNS)
    return [float(value) for value in model.predict(dataset)]


def _public_stats(stats: dict) -> dict:
    return {key: value for key, value in stats.items() if key != "curve"}


def _model_book(records: list[dict], threshold: float) -> dict:
    chosen = []
    for record in records:
        try:
            score = float(record["score"])
        except (TypeError, ValueError, KeyError):
            continue
        if score >= threshold:
            chosen.append(record)
    stats = event_stats(chosen)
    account = simulate(chosen)
    stats["final_equity"] = account["final_equity"]
    stats["max_drawdown"] = account["max_drawdown"]
    stats["n_trades"] = account["n_trades"]
    stats["curve"] = account["curve"]
    return stats


def _write_curve(path: Path, curve: list[dict]) -> None:
    pd.DataFrame(curve).to_csv(path, index=False)


def walk_forward(events_path: str, out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = load_events(events_path)
    meta = {"columns": FEATURE_COLUMNS}
    (out / "feature.meta").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    reports = []
    last_model = None
    for fold in iter_folds():
        train_frame = _subset(frame, lambda row, fold=fold: select_train(row, fold))
        val_frame = _subset(frame, lambda row, fold=fold: select_val(row, fold))
        test_frame = _subset(frame, lambda row, fold=fold: select_test(row, fold))
        report = {
            "fold": fold["name"],
            "n_train": int(len(train_frame)),
            "n_val": int(len(val_frame)),
            "n_test": int(len(test_frame)),
        }
        if len(train_frame) < 2 or len(val_frame) == 0 or len(test_frame) == 0:
            report["status"] = "skipped_not_enough_rows"
            reports.append(report)
            print(f"[train] {fold['name']} skipped train={len(train_frame)} val={len(val_frame)} test={len(test_frame)}")
            continue
        try:
            model = _fit(train_frame)
        except ValueError as exc:
            report["status"] = "skipped_single_class"
            report["reason"] = str(exc)
            reports.append(report)
            print(f"[train] {fold['name']} {exc}")
            continue
        model_path = out / f"model_{fold['name']}.json"
        model.save_model(model_path)
        last_model = model

        val_records = _records(val_frame)
        for record, score in zip(val_records, _predict(model, val_frame)):
            record["score"] = score
        picked = choose_threshold(val_records)
        report["threshold"] = None if picked is None else picked
        test_records = _records(test_frame)
        for record, score in zip(test_records, _predict(model, test_frame)):
            record["score"] = score
        books = summarize(test_records)
        if picked is None:
            model_stats = {"n": 0, "mean_net_return": None, "win_rate": None, "n_trades": 0, "final_equity": 1.0, "max_drawdown": 0.0, "curve": []}
            report["status"] = "no_threshold"
        else:
            model_stats = _model_book(test_records, picked["threshold"])
            report["status"] = "ok"
        report["test"] = {
            "all_buys": _public_stats(books["all_buys"]),
            "strict_type1": _public_stats(books["strict_type1"]),
            "model": _public_stats(model_stats),
        }
        _write_curve(out / f"equity_{fold['name']}_all.csv", books["all_buys"]["curve"])
        _write_curve(out / f"equity_{fold['name']}_strict.csv", books["strict_type1"]["curve"])
        _write_curve(out / f"equity_{fold['name']}_model.csv", model_stats["curve"])
        reports.append(report)
        print(
            f"[train] {fold['name']} status={report['status']} "
            f"train={report['n_train']} val={report['n_val']} test={report['n_test']}"
        )

    if last_model is not None:
        last_model.save_model(out / "model.json")
    payload = {"folds": reports}
    (out / "walkforward.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
