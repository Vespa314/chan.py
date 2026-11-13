"""研究入口。

在 chan.py 根目录运行：

    python -m Research.run sample --codes-file codes.txt --begin 2018-01-01 --end 2024-12-31 --out Research/output/events.csv
    python -m Research.run baseline --events Research/output/events.csv --out Research/output/baseline.json
    python -m Research.run train --events Research/output/events.csv --out Research/output
    python -m Research.run score --code 000001.XSHE --begin 2018-01-01 --end 2024-06-30 --model Research/output/model.json --meta Research/output/feature.meta

打分的起始日必须和采样一致。只喂 2024 年的 K 线，前面的笔、线段和中枢都没有，买卖点会对不上。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from Research.baseline import summarize
from Research.config import DEFAULT_CODES


def _load_codes(args) -> list[str]:
    if args.codes:
        return [item.strip() for item in args.codes.split(",") if item.strip()]
    if args.codes_file:
        lines = Path(args.codes_file).read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    print("[sample] 未指定股票池，使用 DEFAULT_CODES。这不是沪深 300。")
    return list(DEFAULT_CODES)


def _cmd_sample(args) -> None:
    from Research.sampler import sample_codes

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sample_codes(_load_codes(args), args.begin, args.end, str(out))


def _cmd_baseline(args) -> None:
    import pandas as pd

    frame = pd.read_csv(args.events)
    records = frame.to_dict(orient="records")
    report = summarize(records)
    # 20 日窗口只比较事件收益，组合仍按主窗口出场。
    longer = []
    for record in records:
        try:
            if int(float(record.get("complete_20", 0))) != 1:
                continue
            ret = float(record.get("net_return_20"))
        except (TypeError, ValueError):
            continue
        if ret == ret:
            longer.append(ret)
    report["all_buys_20"] = {
        "n": len(longer),
        "mean_net_return": None if not longer else sum(longer) / len(longer),
        "win_rate": None if not longer else sum(value > 0 for value in longer) / len(longer),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    public = json.loads(json.dumps(report, default=str))
    for name in ("all_buys", "strict_type1"):
        curve = public[name].pop("curve", [])
        pd.DataFrame(curve).to_csv(out.with_name(out.stem + f"_{name}_equity.csv"), index=False)
    out.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(public, ensure_ascii=False, indent=2))


def _cmd_train(args) -> None:
    from Research.train import walk_forward

    payload = walk_forward(args.events, args.out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _cmd_score(args) -> None:
    import xgboost as xgb

    from Research.infer import load_columns, replay_trigger_load

    model = xgb.Booster()
    model.load_model(args.model)
    columns = load_columns(args.meta)
    scored = replay_trigger_load(args.code, args.begin, args.end, model, columns)
    for item in scored:
        print(item["time"], f"{item['score']:.6f}", item["bsp_klu_idx"])
    print(f"[score] n={len(scored)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="缠论买卖点研究：采样、基线、滚动训练、推理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sample = sub.add_parser("sample")
    sample.add_argument("--codes", default="")
    sample.add_argument("--codes-file", default="")
    sample.add_argument("--begin", default="2018-01-01")
    sample.add_argument("--end", default="2024-12-31")
    sample.add_argument("--out", default="Research/output/events.csv")
    sample.set_defaults(func=_cmd_sample)

    baseline = sub.add_parser("baseline")
    baseline.add_argument("--events", default="Research/output/events.csv")
    baseline.add_argument("--out", default="Research/output/baseline.json")
    baseline.set_defaults(func=_cmd_baseline)

    train = sub.add_parser("train")
    train.add_argument("--events", default="Research/output/events.csv")
    train.add_argument("--out", default="Research/output")
    train.set_defaults(func=_cmd_train)

    score = sub.add_parser("score")
    score.add_argument("--code", required=True)
    score.add_argument("--begin", default="2018-01-01", help="必须与采样起始日一致，否则缠论结构不同")
    score.add_argument("--end", default="2024-06-30")
    score.add_argument("--model", default="Research/output/model.json")
    score.add_argument("--meta", default="Research/output/feature.meta")
    score.set_defaults(func=_cmd_score)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
