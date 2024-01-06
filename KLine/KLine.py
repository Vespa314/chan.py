from Combiner.KLine_Combiner import CKLine_Combiner
from Common.CEnum import FX_CHECK_METHOD, FX_TYPE, KLINE_DIR
from Common.ChanException import CChanException, ErrCode
from Common.func_util import has_overlap
from KLine.KLine_Unit import CKLine_Unit


# 合并后的K线
class CKLine(CKLine_Combiner[CKLine_Unit]):
    def __init__(self, kl_unit: CKLine_Unit, idx, _dir=KLINE_DIR.UP):
        super(CKLine, self).__init__(kl_unit, _dir)
        self.idx: int = idx
        self.kl_type = kl_unit.kl_type
        kl_unit.set_klc(self)

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

    def get_klu_max_high(self) -> float:
        return max(x.high for x in self.lst)

    def get_klu_min_low(self) -> float:
        return min(x.low for x in self.lst)

    def has_gap_with_next(self) -> bool:
        assert self.next is not None
        # 相同也算重叠，也就是没有gap
        return not has_overlap(self.get_klu_min_low(), self.get_klu_max_high(), self.next.get_klu_min_low(), self.next.get_klu_max_high(), equal=True)

    def check_fx_valid(self, item2: "CKLine", method, for_virtual=False):
        # for_virtual: 虚笔时使用
        assert self.next is not None and item2.pre is not None
        assert self.pre is not None
        assert item2.idx > self.idx
        if self.fx == FX_TYPE.TOP:
            assert for_virtual or item2.fx == FX_TYPE.BOTTOM
            if for_virtual and item2.dir != KLINE_DIR.DOWN:
                return False
            if method == FX_CHECK_METHOD.HALF:  # 检测前两KLC
                item2_high = max([item2.pre.high, item2.high])
                self_low = min([self.low, self.next.low])
            elif method == FX_CHECK_METHOD.LOSS:  # 只检测顶底分形KLC
                item2_high = item2.high
                self_low = self.low
            elif method in (FX_CHECK_METHOD.STRICT, FX_CHECK_METHOD.TOTALLY):
                if for_virtual:
                    item2_high = max([item2.pre.high, item2.high])
                else:
                    assert item2.next is not None
                    item2_high = max([item2.pre.high, item2.high, item2.next.high])
                self_low = min([self.pre.low, self.low, self.next.low])
            else:
                raise CChanException("bi_fx_check config error!", ErrCode.CONFIG_ERROR)
            if method == FX_CHECK_METHOD.TOTALLY:
                return self.low > item2_high
            else:
                return self.high > item2_high and item2.low < self_low
        elif self.fx == FX_TYPE.BOTTOM:
            assert for_virtual or item2.fx == FX_TYPE.TOP
            if for_virtual and item2.dir != KLINE_DIR.UP:
                return False
            if method == FX_CHECK_METHOD.HALF:
                item2_low = min([item2.pre.low, item2.low])
                cur_high = max([self.high, self.next.high])
            elif method == FX_CHECK_METHOD.LOSS:
                item2_low = item2.low
                cur_high = self.high
            elif method in (FX_CHECK_METHOD.STRICT, FX_CHECK_METHOD.TOTALLY):
                if for_virtual:
                    item2_low = min([item2.pre.low, item2.low])
                else:
                    assert item2.next is not None
                    item2_low = min([item2.pre.low, item2.low, item2.next.low])
                cur_high = max([self.pre.high, self.high, self.next.high])
            else:
                raise CChanException("bi_fx_check config error!", ErrCode.CONFIG_ERROR)
            if method == FX_CHECK_METHOD.TOTALLY:
                return self.high < item2_low
            else:
                return self.low < item2_low and item2.high > cur_high
        else:
            raise CChanException("only top/bottom fx can check_valid_top_button", ErrCode.BI_ERR)
