import os
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/..')

from Trade.Script.StaticsChanConfig import MONITOR_CONFIG  # noqa: E402


def BACKTEST_CONFIG():
    static_config = MONITOR_CONFIG()
    static_config["print_warming"] = False
    static_config["only_judge_last"] = False
    static_config["min_zs_cnt"] = 0
    static_config["bs1_peak"] = False
    static_config["stragety_para-sell"]["short_shelling"] = True
    return static_config
