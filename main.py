from chan import CChan
from common.CEnum import KL_TYPE
from plot.plotDriver import CPlot_driver
from plot.animatePlotDriver import CAnimate_driver
from ChanConfig import CChanConfig
from stragety.CustomStragety import CCustomStragety

if __name__ == "__main__":
    code = "sh.600000"
    begin_time = "2020-01-01"
    end_time = None
    data_src = "custom:CustomDataDemo.CStockFileReader"
    lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_60M]

    config = CChanConfig({
                        "zs_mode": "bi",
                        "zs_combine": True,
                        "zs_combine_mode": "zs",
                        "bi_strict": True,
                        "mean_metrics": [],
                        "triger_step": False,
                        "skip_step": 0,
                        "seg_algo": "break",
                        "divergence_rate": 0.9,
                        "min_zs_cnt": 1,
                        "max_bs2_rate": 0.618,
                        "bs1_peak": True,
                        "macd_algo": "peak",
                        "bs_type": '1,2,3,2s,1p',
                        "stragety_cls": CCustomStragety,
                        "only_judge_last": False,
                        "stragety_para": {
                            "strict_open": True,
                            "use_qjt": True,
                            "cover_stragety": "bsp",
                            "short_shelling": True,
                        }
    })

    plot_config = {
        "plot_kline": False,
        "plot_kline_combine": False,
        "plot_bi": True,
        "plot_seg": True,
        "plot_eigen": False,
        "plot_zs": True,
        "plot_macd": False,
        "plot_mean": False,
        "plot_bsp": True,
        "plot_cbsp": True,
        "plot_extrainfo": False,
    }

    plot_para = {
        "zs_color": "orange",
        "zs_linewidth": 3,
        "seg_color": "g",
        "bi_show_num": False,
        "bi_num_color": 'green',
        "figure_w": 24,
        "figure_h": 10,
        # "figure_x_range": 10,
        # "seg_sub_lv_cnt": 2,
        # "bi_sub_lv_cnt": 3,
    }

    chan = CChan(code=code, begin_time=begin_time, end_time=end_time, data_src=data_src, lv_list=lv_list, config=config)

    if not config.triger_step:
        plot_driver = CPlot_driver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        # plot_driver.save2img("/home/ubuntu/data/Download/tmp/demo.png")
    else:
        CAnimate_driver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
