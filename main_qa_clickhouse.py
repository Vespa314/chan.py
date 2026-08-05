"""从 ClickHouse 读数并用 QtPlotDriver 画图（对齐 main.py 用法）。

用法::

    ~/MyProject/quantaxis/.venv/bin/python main_qa_clickhouse.py
    QT_QPA_PLATFORM=offscreen .../python main_qa_clickhouse.py --no-show
"""

from __future__ import annotations

import argparse
import os

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.QtPlotDriver import CQtPlotDriver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="sz.000001", help="股票代码，支持 sz.000001 / 000001")
    parser.add_argument("--begin", default="2018-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="结束日期，默认至今")
    parser.add_argument("--out", default="./test_qa_clickhouse_qt.png", help="导出图片路径")
    parser.add_argument("--no-show", action="store_true", help="只导出图片，不进入事件循环")
    args = parser.parse_args()

    config = CChanConfig({
        "bi_strict": True,
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": "1,2,3a,1p,2s,3b",
        "print_warning": True,
        "zs_algo": "normal",
    })

    plot_config = {
        "plot_kline": True,
        "plot_kline_combine": True,
        "plot_bi": True,
        "plot_seg": True,
        "plot_eigen": False,
        "plot_zs": True,
        "plot_macd": False,
        "plot_mean": False,
        "plot_channel": False,
        "plot_bsp": True,
        "plot_demark": False,
        "plot_marker": False,
        "plot_rsi": False,
        "plot_kdj": False,
    }

    plot_para = {
        "seg": {},
        "bi": {},
        "figure": {
            "x_range": 200,
        },
        "marker": {},
    }

    chan = CChan(
        code=args.code,
        begin_time=args.begin,
        end_time=args.end,
        data_src=DATA_SRC.QAClickhouse,
        lv_list=[KL_TYPE.K_DAY],
        config=config,
        autype=AUTYPE.QFQ,
    )

    driver = CQtPlotDriver(
        chan,
        plot_config=plot_config,
        plot_para=plot_para,
    )
    out_path = args.out if os.path.isabs(args.out) else os.path.abspath(args.out)
    driver.save2img(out_path)
    n_klu = sum(len(klc.lst) for klc in chan[0].lst)
    print(f"saved: {out_path}")
    print(f"klu={n_klu}, bi={len(chan[0].bi_list)}, seg={len(chan[0].seg_list)}")
    if not args.no_show:
        driver.show()


if __name__ == "__main__":
    main()
