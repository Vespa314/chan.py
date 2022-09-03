import os
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/../..')

from CustomBuySellPoint.CustomStragety import CCustomStragety  # noqa: E402


def MONITOR_CONFIG():
    return {
        "zs_combine": True,
        "zs_combine_mode": "zs",  # zs/peak
        "one_bi_zs": True,

        "bi_strict": True,
        "bi_fx_check": "strict",  # strict/loss/half

        "mean_metrics": [5, 8, 20, 34, 60, 120],
        "trend_metrics": [5, 8, 20, 34, 60, 120],
        "boll_n": 20,

        "triger_step": False,
        "skip_step": 0,

        "kl_data_check": True,
        "max_kl_misalgin_cnt": 2,
        "max_kl_inconsistent_cnt": 5,
        "auto_skip_illegal_sub_lv": True,
        "print_warming": True,
        "print_err_time": True,

        "seg_algo": "chan",  # chan, 1+1, break
        "left_seg_method": "peak",  # all/peak

        "cbsp_stragety": CCustomStragety,
        "only_judge_last": True,

        "model": None,
        "cal_feature": True,
        "cal_cover": False,
        "cbsp_chek_active": True,
        "print_inactive_reason": False,

        "od_win_width": 100,
        "od_mean_thred": 3.0,
        "od_max_zero_cnt": None,
        "od_skip_zero": True,

        "stock_no_active_day": 30,
        "stock_no_active_thred": 3,
        "stock_distinct_price_thred": 25,

        # 下面支持配置buy/sell/segbuy/segsell
        "divergence_rate": float("inf"),
        "bsp1_only_multibi_zs": True,
        "min_zs_cnt": 1,  # buy sell point
        "max_bs2_rate": 1.0,  # 2买那一笔最大回拉比例
        "bs1_peak": True,
        "macd_algo": "peak",  # peak/area/full_area/diff/slope/amp
        "bs_type": '1,2,3,2s,1p',
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "score_thred": None,

        "divergence_rate-seg": float("inf"),
        "min_zs_cnt-seg": 0,  # buy sell point
        "max_bs2_rate-seg": 1-1e-7,  # 2买那一笔最大回拉比例
        "bs1_peak-seg": False,
        "macd_algo-seg": "amp",
        "bsp2_follow_1-seg": False,
        "bsp3_follow_1-seg": False,
        "bsp3_peak": False,
        "bsp3_peak-seg": False,
        "bsp2s_follow_2": False,
        "bsp2s_follow_2-seg": False,
        "strict_bsp3": False,
        "strict_bsp3-seg": False,

        "stragety_para-buy": {
            "strict_open": False,
            "use_qjt": False,
            "judge_on_close": True,
            "max_sl_rate": None,
            "max_profit_rate": None,
        },
        "stragety_para-sell": {
            "strict_open": False,
            "use_qjt": False,
            "short_shelling": False,
            "judge_on_close": True,
            "max_sl_rate": None,
            "max_profit_rate": None,
        }
    }
