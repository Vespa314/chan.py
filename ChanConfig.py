from Bi.BiConfig import CBiConfig
from BuySellPoint.BSPointConfig import CBSPointConfig
from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import _parse_inf
from Config.EnvConfig import Env
from Math.BOLL import BollModel
from Math.MACD import CMACD
from Math.TrendModel import CTrendModel
from Seg.SegConfig import CSegConfig
from ZS.ZSConfig import CZSConfig


class CChanConfig:
    """
    conf = {
        "zs_combine": True,
        "zs_combine_mode": "zs",  # zs/peak
        "one_bi_zs": False,

        "bi_strict": True,
        "bi_fx_check": "strict",  # strict/loss/half

        "mean_metrics": [],
        "trend_metrics": [],
        "boll_n": 20,

        "triger_step": False,
        "skip_step": 0,

        "kl_data_check": True,
        "max_kl_misalgin_cnt": 2,
        "max_kl_inconsistent_cnt": 5,
        "auto_skip_illegal_sub_lv": False,
        "print_warming": True,
        "print_err_time": False,

        "seg_algo": "chan", # chan, 1+1, break
        "left_seg_method": "peak", # all/peak

        "cbsp_stragety": None,
        "only_judge_last": False,

        "model": None,
        "cal_feature": False,
        "cal_cover": True,
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
        "divergence_rate": 0.9,
        "min_zs_cnt": 1,  # buy sell point
        "bsp1_only_multibi_zs": True,
        "max_bs2_rate": 0.618, # 2买那一笔最大回拉比例
        "bs1_peak": True,
        "macd_algo": "peak",  # peak/area/full_area/diff/slope/amp/amount/volumn/amount_avg/volumn_avg/turnrate_avg
        "bs_type": '1,2,3,2s,1p',
        "bsp2_follow_1" : True,
        "bsp3_follow_1" : True,
        "bsp3_peak" : False,
        "bsp2s_follow_2" : False,
        "strict_bsp3": False,
        "score_thred": None
        "stragety_para":{
            "strict_open": True,
            "use_qjt": True,
            "short_shelling": True,
            "judge_on_close": True,
            "max_sl_rate": None,
            "max_profit_rate": None,
        }
    }
    """
    def __init__(self, conf=None):
        if conf is None:
            conf = {}
        conf = ConfigWithCheck(conf)
        self.bi_conf = CBiConfig(
                is_strict=conf.get("bi_strict", True),
                bi_fx_check=conf.get("bi_fx_check", "strict"),
            )
        self.seg_conf = CSegConfig(
                seg_algo=conf.get("seg_algo", "chan"),
                left_method=conf.get("left_seg_method", "peak"),
            )
        self.zs_conf = CZSConfig(
                need_combine=conf.get("zs_combine", True),
                zs_combine_mode=conf.get("zs_combine_mode", "zs"),
                one_bi_zs=conf.get("one_bi_zs", False),
            )

        self.triger_step = conf.get("triger_step", False)
        self.skip_step = conf.get("skip_step", 0)

        self.kl_data_check = conf.get("kl_data_check", True)
        self.max_kl_misalgin_cnt = conf.get("max_kl_misalgin_cnt", 2)
        self.max_kl_inconsistent_cnt = conf.get("max_kl_inconsistent_cnt", 5)
        self.auto_skip_illegal_sub_lv = conf.get("auto_skip_illegal_sub_lv", False)
        self.print_warming = conf.get("print_warming", True)
        self.print_err_time = conf.get("print_err_time", False)

        self.no_active_metric = {
            "no_active_day": conf.get("stock_no_active_day", 30),
            "no_active_thred": conf.get("stock_no_active_thred", 3),
            "distinct_price_thred": conf.get("stock_distinct_price_thred", 25),
        }

        self.mean_metrics = conf.get("mean_metrics", [])
        self.trend_metrics = conf.get("trend_metrics", [])
        self.boll_n = conf.get("boll_n", 20)
        self.cbsp_stragety = conf.get("cbsp_stragety", None)
        self.cal_cover = conf.get("cal_cover", True)
        self.cbsp_chek_active = conf.get("cbsp_chek_active", True)
        self.print_inactive_reason = conf.get("print_inactive_reason", False)

        self.model = conf.get("model", None)
        self.set_env_cal_feature(conf)

        self.od_win_width = conf.get("od_win_width", 100)
        self.od_mean_thred = conf.get("od_mean_thred", 3.0)
        self.od_max_zero_cnt = conf.get("od_max_zero_cnt", None)
        self.od_skip_zero = conf.get("od_skip_zero", True)

        self.only_judge_last = conf.get("only_judge_last", False)

        self.set_bsp_config(conf)

        conf.check()

    def set_env_cal_feature(self, conf):
        if "cal_feature" in conf.conf:
            Env.cal_feature = conf.get("cal_feature", False)
            if (self.model or self.cbsp_stragety is not None) and not Env.cal_feature:
                Env.cal_feature = True
                print("[WARMING]Env.cal_feature→True, because model is not None")
        elif self.model or self.cbsp_stragety is not None:
            Env.cal_feature = True

    def GetMetricModel(self):
        res = [CMACD()]
        res.extend(CTrendModel(TREND_TYPE.MEAN, mean_T) for mean_T in self.mean_metrics)

        for trend_T in self.trend_metrics:
            res.append(CTrendModel(TREND_TYPE.MAX, trend_T))
            res.append(CTrendModel(TREND_TYPE.MIN, trend_T))
        res.append(BollModel(self.boll_n))
        return res

    def set_bsp_config(self, conf):
        para_dict = {
            "divergence_rate": 0.9,
            "min_zs_cnt": 1,
            "bsp1_only_multibi_zs": True,
            "max_bs2_rate": 0.618,
            "macd_algo": "peak",
            "bs1_peak": True,
            "stragety_para": {},
            "bs_type": "1,2,3,2s,1p",
            "bsp2_follow_1": True,
            "bsp3_follow_1": True,
            "bsp3_peak": False,
            "bsp2s_follow_2": False,
            "strict_bsp3": False,
            "score_thred": None,
            }
        args = {para: conf.get(para, default_value) for para, default_value in para_dict.items()}
        self.bs_point_conf = CBSPointConfig(**args)

        self.seg_bs_point_conf = CBSPointConfig(**args)
        self.seg_bs_point_conf.b_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.s_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.b_conf.set("bsp1_only_multibi_zs", False)
        self.seg_bs_point_conf.s_conf.set("bsp1_only_multibi_zs", False)

        for k, v in conf.items():
            if type(v) == str:
                v = f'"{v}"'
            v = _parse_inf(v)
            if k.endswith("-buy"):
                prop = k.replace("-buy", "")
                exec(f"self.bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-sell"):
                prop = k.replace("-sell", "")
                exec(f"self.bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-segbuy"):
                prop = k.replace("-segbuy", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-segsell"):
                prop = k.replace("-segsell", "")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-seg"):
                prop = k.replace("-seg", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k in args:
                exec(f"self.bs_point_conf.b_conf.set({k}, {v})")
                exec(f"self.bs_point_conf.s_conf.set({k}, {v})")
            else:
                raise CChanException(f"unknown para = {k}", ErrCode.PARA_ERROR)
        self.bs_point_conf.b_conf.parse_target_type()
        self.bs_point_conf.s_conf.parse_target_type()


class ConfigWithCheck:
    def __init__(self, conf):
        self.conf = conf

    def get(self, k, default_value=None):
        res = self.conf.get(k, default_value)
        if k in self.conf:
            del self.conf[k]
        return res

    def items(self):
        visit_keys = set()
        for k, v in self.conf.items():
            yield k, v
            visit_keys.add(k)
        for k in visit_keys:
            del self.conf[k]

    def check(self):
        if len(self.conf) > 0:
            invalid_key_lst = ",".join(list(self.conf.keys()))
            raise CChanException(f"invalid CChanConfig: {invalid_key_lst}", ErrCode.PARA_ERROR)
