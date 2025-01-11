from typing import List

from Bi.BiConfig import CBiConfig
from BuySellPoint.BSPointConfig import CBSPointConfig
from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import _parse_inf
from Math.BOLL import BollModel
from Math.Demark import CDemarkEngine
from Math.KDJ import KDJ
from Math.MACD import CMACD
from Math.RSI import RSI
from Math.TrendModel import CTrendModel
from Seg.SegConfig import CSegConfig
from ZS.ZSConfig import CZSConfig


class CChanConfig:
    def __init__(self, conf=None):
        if conf is None:
            conf = {}
        conf = ConfigWithCheck(conf)
        self.bi_conf = CBiConfig(
            bi_algo=conf.get("bi_algo", "normal"),
            is_strict=conf.get("bi_strict", True),
            bi_fx_check=conf.get("bi_fx_check", "strict"),
            gap_as_kl=conf.get("gap_as_kl", False),
            bi_end_is_peak=conf.get('bi_end_is_peak', True),
            bi_allow_sub_peak=conf.get("bi_allow_sub_peak", True),
        )
        self.seg_conf = CSegConfig(
            seg_algo=conf.get("seg_algo", "chan"),
            left_method=conf.get("left_seg_method", "peak"),
        )
        self.zs_conf = CZSConfig(
            need_combine=conf.get("zs_combine", True),
            zs_combine_mode=conf.get("zs_combine_mode", "zs"),
            one_bi_zs=conf.get("one_bi_zs", False),
            zs_algo=conf.get("zs_algo", "normal"),
        )

        self.trigger_step = conf.get("trigger_step", False)
        self.skip_step = conf.get("skip_step", 0)

        self.kl_data_check = conf.get("kl_data_check", True)
        self.max_kl_misalgin_cnt = conf.get("max_kl_misalgin_cnt", 2)
        self.max_kl_inconsistent_cnt = conf.get("max_kl_inconsistent_cnt", 5)
        self.auto_skip_illegal_sub_lv = conf.get("auto_skip_illegal_sub_lv", False)
        self.print_warning = conf.get("print_warning", True)
        self.print_err_time = conf.get("print_err_time", True)

        self.mean_metrics: List[int] = conf.get("mean_metrics", [])
        self.trend_metrics: List[int] = conf.get("trend_metrics", [])
        self.macd_config = conf.get("macd", {"fast": 12, "slow": 26, "signal": 9})
        self.cal_demark = conf.get("cal_demark", False)
        self.cal_rsi = conf.get("cal_rsi", False)
        self.cal_kdj = conf.get("cal_kdj", False)
        self.rsi_cycle = conf.get("rsi_cycle", 14)
        self.kdj_cycle = conf.get("kdj_cycle", 9)
        self.demark_config = conf.get("demark", {
            'demark_len': 9,
            'setup_bias': 4,
            'countdown_bias': 2,
            'max_countdown': 13,
            'tiaokong_st': True,
            'setup_cmp2close': True,
            'countdown_cmp2close': True,
        })
        self.boll_n = conf.get("boll_n", 20)

        self.set_bsp_config(conf)

        conf.check()

    def GetMetricModel(self):
        res: List[CMACD | CTrendModel | BollModel | CDemarkEngine | RSI | KDJ] = [
            CMACD(
                fastperiod=self.macd_config['fast'],
                slowperiod=self.macd_config['slow'],
                signalperiod=self.macd_config['signal'],
            )
        ]
        res.extend(CTrendModel(TREND_TYPE.MEAN, mean_T) for mean_T in self.mean_metrics)

        for trend_T in self.trend_metrics:
            res.append(CTrendModel(TREND_TYPE.MAX, trend_T))
            res.append(CTrendModel(TREND_TYPE.MIN, trend_T))
        res.append(BollModel(self.boll_n))
        if self.cal_demark:
            res.append(CDemarkEngine(
                demark_len=self.demark_config['demark_len'],
                setup_bias=self.demark_config['setup_bias'],
                countdown_bias=self.demark_config['countdown_bias'],
                max_countdown=self.demark_config['max_countdown'],
                tiaokong_st=self.demark_config['tiaokong_st'],
                setup_cmp2close=self.demark_config['setup_cmp2close'],
                countdown_cmp2close=self.demark_config['countdown_cmp2close'],
            ))
        if self.cal_rsi:
            res.append(RSI(self.rsi_cycle))
        if self.cal_kdj:
            res.append(KDJ(self.kdj_cycle))
        return res

    def set_bsp_config(self, conf):
        para_dict = {
            "divergence_rate": float("inf"),
            "min_zs_cnt": 1,
            "bsp1_only_multibi_zs": True,
            "max_bs2_rate": 0.9999,
            "macd_algo": "peak",
            "bs1_peak": True,
            "bs_type": "1,1p,2,2s,3a,3b",
            "bsp2_follow_1": True,
            "bsp3_follow_1": True,
            "bsp3_peak": False,
            "bsp2s_follow_2": False,
            "max_bsp2s_lv": None,
            "strict_bsp3": False,
        }
        args = {para: conf.get(para, default_value) for para, default_value in para_dict.items()}
        self.bs_point_conf = CBSPointConfig(**args)

        self.seg_bs_point_conf = CBSPointConfig(**args)
        self.seg_bs_point_conf.b_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.s_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.b_conf.set("bsp1_only_multibi_zs", False)
        self.seg_bs_point_conf.s_conf.set("bsp1_only_multibi_zs", False)

        for k, v in conf.items():
            if isinstance(v, str):
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
        self.seg_bs_point_conf.b_conf.parse_target_type()
        self.seg_bs_point_conf.s_conf.parse_target_type()


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
