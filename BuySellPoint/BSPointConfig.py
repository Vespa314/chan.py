from typing import Dict, List, Optional

from Common.CEnum import BSP_TYPE, MACD_ALGO
from Common.func_util import _parse_inf


class CBSPointConfig:
    def __init__(self, **args):
        self.b_conf = CPointConfig(**args)
        self.s_conf = CPointConfig(**args)

    def GetBSConfig(self, is_buy):
        return self.b_conf if is_buy else self.s_conf


class CPointConfig:
    def __init__(self,
                 divergence_rate,
                 min_zs_cnt,
                 bsp1_only_multibi_zs,
                 max_bs2_rate,
                 macd_algo,
                 bs1_peak,
                 bs_type,
                 bsp2_follow_1,
                 bsp3_follow_1,
                 bsp3_peak,
                 bsp2s_follow_2,
                 max_bsp2s_lv,
                 strict_bsp3,
                 ):
        self.divergence_rate = divergence_rate
        self.min_zs_cnt = min_zs_cnt
        self.bsp1_only_multibi_zs = bsp1_only_multibi_zs
        self.max_bs2_rate = max_bs2_rate
        assert self.max_bs2_rate <= 1
        self.SetMacdAlgo(macd_algo)
        self.bs1_peak = bs1_peak
        self.tmp_target_types = bs_type
        self.target_types: List[BSP_TYPE] = []
        self.bsp2_follow_1 = bsp2_follow_1
        self.bsp3_follow_1 = bsp3_follow_1
        self.bsp3_peak = bsp3_peak
        self.bsp2s_follow_2 = bsp2s_follow_2
        self.max_bsp2s_lv: Optional[int] = max_bsp2s_lv
        self.strict_bsp3 = strict_bsp3

    def parse_target_type(self):
        _d: Dict[str, BSP_TYPE] = {x.value: x for x in BSP_TYPE}
        if isinstance(self.tmp_target_types, str):
            self.tmp_target_types = [t.strip() for t in self.tmp_target_types.split(",")]
        for target_t in self.tmp_target_types:
            assert target_t in ['1', '2', '3a', '2s', '1p', '3b']
        self.target_types = [_d[_type] for _type in self.tmp_target_types]

    def SetMacdAlgo(self, macd_algo):
        _d = {
            "area": MACD_ALGO.AREA,
            "peak": MACD_ALGO.PEAK,
            "full_area": MACD_ALGO.FULL_AREA,
            "diff": MACD_ALGO.DIFF,
            "slope": MACD_ALGO.SLOPE,
            "amp": MACD_ALGO.AMP,
            "amount": MACD_ALGO.AMOUNT,
            "volumn": MACD_ALGO.VOLUMN,
            "amount_avg": MACD_ALGO.AMOUNT_AVG,
            "volumn_avg": MACD_ALGO.VOLUMN_AVG,
            "turnrate_avg": MACD_ALGO.AMOUNT_AVG,
            "rsi": MACD_ALGO.RSI,
        }
        self.macd_algo = _d[macd_algo]

    def set(self, k, v):
        v = _parse_inf(v)
        if k == "macd_algo":
            self.SetMacdAlgo(v)
        else:
            exec(f"self.{k} = {v}")
