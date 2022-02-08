from combiner.CKLine_Combiner import CKLine_Combiner
from common.CEnum import FX_TYPE, BI_DIR


class CEigen(CKLine_Combiner):
    def __init__(self, bi, _dir):
        super(CEigen, self).__init__(bi, _dir)
        self.gap = False

    def update_fx(self, _pre, _next, exclude_included=False):
        super(CEigen, self).update_fx(_pre, _next, exclude_included)
        if (self.fx == FX_TYPE.TOP and _pre.high < self.low) or \
           (self.fx == FX_TYPE.BOTTOM and _pre.low > self.high):
            self.gap = True

    def __str__(self):
        # return f"{self.lst[0].begin_klc.lst[0].time}~{self.lst[-1].end_klc.lst[-1].time} {self.low}->{self.high} gap={self.gap} fx={self.fx}"
        return f"{self.lst[0].idx}~{self.lst[-1].idx} gap={self.gap} fx={self.fx}"

    def GetPeakBiIdx(self):
        assert self.fx != FX_TYPE.UNKNOWN
        bi_dir = self.lst[0].dir
        if bi_dir == BI_DIR.UP:  # 下降线段
            return self.get_peak_klu(is_high=False).idx-1
        else:
            return self.get_peak_klu(is_high=True).idx-1
