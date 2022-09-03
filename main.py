from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.XGBModel import CXGBModel
from Common.CEnum import AUTYPE, KL_TYPE
from Config.EnvConfig import Env
from CustomBuySellPoint.CustomStragety import CCustomStragety
from Plot.AnimatePlotDriver import CAnimateDriver
from Plot.PlotDriver import CPlotDriver

if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2018-01-01"
    end_time = None
    data_src = "custom:OfflineDataAPI.CStockFileReader"
    # data_src = DATA_SRC.AK_SHARE
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "zs_combine": True,
        "zs_combine_mode": "zs",
        "bi_strict": True,
        "triger_step": False,
        "skip_step": 0,
        "seg_algo": "chan",
        "mean_metrics": [5, 8, 20, 34, 60, 120],  # 如果改了，模型要重新训
        "trend_metrics": [5, 8, 20, 34, 60, 120],
        "boll_n": 20,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "max_bs2_rate-buy": 1-1e-7,
        "max_bs2_rate-sell": 1-1e-7,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": '1,2,3,1p,2s',
        "print_inactive_reason": False,
        "cbsp_stragety": CCustomStragety,
        "auto_skip_illegal_sub_lv": True,
        "print_warming": True,
        "od_win_width": 100,
        "od_mean_thred": 3.0,
        "od_max_zero_cnt": None,
        "od_skip_zero": True,
        "cal_feature": True,
        "model": CXGBModel(f"{Env.MODEL_PATH}", model_tag=Env.MODEL['model_tag'], model_type=Env.MODEL['model_type']),
        "only_judge_last": False,
        "divergence_rate-seg": float("inf"),
        "min_zs_cnt-seg": 0,  # buy sell point
        "max_bs2_rate-seg": 1-1e-7,  # 2买那一笔最大回拉比例
        "bs1_peak-seg": False,
        "macd_algo-seg": "amp",
        "bsp2_follow_1-seg": False,
        "bsp3_follow_1-seg": False,
        "stragety_para-buy": {
            "strict_open": False,
            "use_qjt": False,
            "judge_on_close": True,  # 如果改了，模型要重新训
            "max_sl_rate": None,
            "max_profit_rate": None,
        },
        "stragety_para-sell": {
            "strict_open": False,
            "use_qjt": False,
            "short_shelling": True,
            "judge_on_close": True,  # 如果改了，模型要重新训
            "max_sl_rate": None,
            "max_profit_rate": None,
        }
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
        "plot_cbsp": True,
        "plot_extrainfo": False,
    }

    plot_para = {
        "seg": {
            "plot_trendline": False,
        },
        "bi": {
            # "show_num": True,
            # "disp_end": True,
        },
        "figure": {
            "x_range": 50,
        },
        "cbsp": {
            # "plot_cover": False,
            # "adjust_text": True,
        },
    }

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
        extra_kl=None,
    )

    if not config.triger_step:
        plot_driver = CPlotDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        # plot_driver.save2img(f"/home/ubuntu/data/Download/chan-{code}.png")
        # plot_driver.ShowDrawFuncHelper()
    else:
        CAnimateDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )

    # chan.auto_save()
