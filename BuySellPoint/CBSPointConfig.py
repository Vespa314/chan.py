class CBSPointConfig:
    def __init__(self, **args):
        self.b_conf = CPointConfig(**args)
        self.s_conf = CPointConfig(**args)

    def GetStragetyPara(self, is_buy, k):
        if is_buy:
            return self.b_conf.GetStragetyPara(k)
        else:
            return self.s_conf.GetStragetyPara(k)


class CPointConfig:
    def __init__(self,
                 divergence_rate,
                 min_zs_cnt,
                 max_bs2_rate,
                 macd_algo,
                 bs1_peak,
                 bs_type,
                 stragety_para,
                 bsp2_follow_1,
                 bsp3_follow_1,
                 bsp2s_follow_2,
                 strict_bsp3,
                 score_thred,
                 ):
        self.divergence_rate = divergence_rate
        self.min_zs_cnt = min_zs_cnt
        # assert self.min_zs_cnt > 0
        self.max_bs2_rate = max_bs2_rate
        assert self.max_bs2_rate <= 1
        self.macd_algo = macd_algo
        self.bs1_peak = bs1_peak
        self.target_types = bs_type
        self.stragety_para = stragety_para
        self.bsp2_follow_1 = bsp2_follow_1
        self.bsp3_follow_1 = bsp3_follow_1
        self.bsp2s_follow_2 = bsp2s_follow_2
        self.strict_bsp3 = strict_bsp3
        self.score_thred = score_thred

    def parse_target_type(self):
        if type(self.target_types) == str:
            self.target_types = [t.strip() for t in self.target_types.split(",")]
        for target_t in self.target_types:
            assert target_t in ['1', '2', '3', '2s', '1p']

    def GetStragetyPara(self, k):
        return self.stragety_para[k]
