import matplotlib.pyplot as plt
from IPython.display import clear_output, display

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import DATA_SRC, KL_TYPE

from .PlotDriver import CPlotDriver


class CAnimateDriver:
    def __init__(self, chan: CChan, plot_config=None, plot_para=None):
        if plot_config is None:
            plot_config = {}
        if plot_para is None:
            plot_para = {}
        for snapshot in chan.step_load():
            g = CPlotDriver(chan, plot_config, plot_para)
            clear_output(wait=True)
            display(g.figure)
            plt.close(g.figure)


if __name__ == "__main__":
    chan_config = CChanConfig({"triger_step": True})
    chan = CChan(
        code="HK.00700",
        begin_time="2020-03-03",
        end_time="2020-09-01",
        data_src=DATA_SRC.FUTU,
        lv_list=[KL_TYPE.K_DAY],
        config=chan_config)
    CAnimateDriver(
        chan,
        plot_config={
            "figure_w": 24,
            "figure_h": 10,
            "plot_kline": True,
            "plot_kline_combine": True,
            "plot_bi": True,
            "plot_seg": True,
            "plot_eigen": False,
            "plot_zs": True,
            "plot_macd": False,
            "plot_mean": False,
        },
        plot_para={
            "zs_color": "orange",
            "zs_linewidth": 3,
            "seg_color": "g",
            "bi_show_num": False,
            "bi_num_color": 'green'
        })
