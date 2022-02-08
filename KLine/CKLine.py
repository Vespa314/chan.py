from combiner.CKLine_Combiner import CKLine_Combiner
from common.CEnum import KLINE_DIR, FX_TYPE


# 合并后的K线
class KLine(CKLine_Combiner):
    def __init__(self, kl_unit, idx, _dir=KLINE_DIR.UP):
        super(KLine, self).__init__(kl_unit, _dir)
        self.idx = idx
        self.kl_type = kl_unit.kl_type
        # 下面是父类成员
        # self.time_begin = kl_unit.time
        # self.time_end = kl_unit.time
        # self.high = kl_unit.high
        # self.low = kl_unit.low
        # self.lst = [kl_unit]  # 本级别每一根单位K线
        # self.dir = _dir
        # self.fx = FX_TYPE.UNKNOWN
        # self.pre
        # self.next
        # 父类方法
        # try_add(self, unit_kl)
        # test_combine(self, _kl)

    def __str__(self):
        fx_token = ""
        if self.fx == FX_TYPE.TOP:
            fx_token = "^"
        elif self.fx == FX_TYPE.BOTTOM:
            fx_token = "_"
        return f"{self.idx}th{fx_token}:{self.time_begin}~{self.time_end}({self.kl_type}|{len(self.lst)}) low={self.low} high={self.high}"

    def GetSubKLC(self):
        # 可能会出现相邻的两个KLC的子KLC会有重复
        # 因为子KLU合并时正好跨过了父KLC的结束时间边界
        last_klc = None
        for klu in self.lst:
            for sub_klu in klu.get_children():
                if sub_klu.klc != last_klc:
                    last_klc = sub_klu.klc
                    yield sub_klu.klc

    def getOutlinearScore(self):
        res = {}
        for klu in self:
            outliner_dict = klu.getOutlinearScore()
            if not res:
                res = outliner_dict
            else:
                for k, v in outliner_dict.items():
                    if v >= res[k]:
                        res[k] = v
        return res

    def GetNegPosCnt(self):
        # 阴线， 阳线数
        res = {"neg": 0, "pos": 0}
        for klu in self:
            if klu.close < klu.open:
                res["neg"] += 1
            else:
                res["pos"] += 1
        res["neg_rate"] = res["neg"]/float(len(self))
        res["pos_rate"] = res["pos"]/float(len(self))
        return res
