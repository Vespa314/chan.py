"""PyQtGraph 画图 demo：与 main.py 配置对齐，导出 PNG 并可选弹窗。

用法（推荐 quantaxis venv）::

    ~/MyProject/quantaxis/.venv/bin/python Debug/qt_plot_demo.py
    QT_QPA_PLATFORM=offscreen .../python Debug/qt_plot_demo.py --no-show
    QT_QPA_PLATFORM=offscreen .../python Debug/qt_plot_demo.py --synthetic --no-show
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_FIELD, DATA_SRC, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from Plot.QtPlotDriver import CQtPlotDriver


def _build_synthetic_klus(count: int = 180) -> List[CKLine_Unit]:
    """构造严格递增日期的合成日线，供离线冒烟。"""
    klus: List[CKLine_Unit] = []
    year, month, day = 2018, 1, 1
    for i in range(count):
        mid = 10.0 + 3.0 * math.sin(i / 8.0) + i * 0.01
        open_p = mid - 0.1
        close = mid + 0.15 * math.cos(i / 5.0)
        high = max(open_p, close) + 0.2
        low = min(open_p, close) - 0.2
        klus.append(
            CKLine_Unit(
                {
                    DATA_FIELD.FIELD_TIME: CTime(year, month, day, 0, 0),
                    DATA_FIELD.FIELD_OPEN: open_p,
                    DATA_FIELD.FIELD_CLOSE: close,
                    DATA_FIELD.FIELD_HIGH: high,
                    DATA_FIELD.FIELD_LOW: low,
                }
            )
        )
        day += 1
        if day > 28:
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1
    return klus


def _build_chan(synthetic: bool) -> CChan:
    plot_ready_conf = {
        "bi_strict": True,
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
    }
    if synthetic:
        config = CChanConfig({**plot_ready_conf, "trigger_step": True})
        chan = CChan(
            code="test.syn",
            begin_time=None,
            end_time=None,
            data_src=DATA_SRC.BAO_STOCK,
            lv_list=[KL_TYPE.K_DAY],
            config=config,
            autype=AUTYPE.QFQ,
        )
        chan.trigger_load({KL_TYPE.K_DAY: _build_synthetic_klus()})
        return chan

    config = CChanConfig({**plot_ready_conf, "trigger_step": False})
    return CChan(
        code="sz.000001",
        begin_time="2018-01-01",
        end_time=None,
        data_src=DATA_SRC.BAO_STOCK,
        lv_list=[KL_TYPE.K_DAY],
        config=config,
        autype=AUTYPE.QFQ,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-show", action="store_true", help="只导出图片")
    parser.add_argument("--synthetic", action="store_true", help="用合成数据，不访问网络")
    parser.add_argument("--out", default="./test_qt.png", help="导出路径")
    args = parser.parse_args()

    plot_config = {
        "plot_kline": True,
        "plot_kline_combine": True,
        "plot_bi": True,
        "plot_seg": True,
        "plot_eigen": False,
        "plot_zs": True,
        "plot_macd": True,
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
        "figure": {"x_range": 120, "w": 16, "h": 8},
        "marker": {},
    }

    chan = _build_chan(synthetic=args.synthetic)
    driver = CQtPlotDriver(chan, plot_config=plot_config, plot_para=plot_para)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    driver.save2img(out_path)
    print(f"saved: {out_path}")
    if not args.no_show:
        driver.show()


if __name__ == "__main__":
    main()
