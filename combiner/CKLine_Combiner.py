from common.CEnum import KLINE_DIR, FX_TYPE
from .CCombine_Item import CCombine_Item
from common.cache import make_cache, add_clear_cache


@add_clear_cache
class CKLine_Combiner:
    def __init__(self, kl_unit, _dir):
        item = CCombine_Item(kl_unit)
        self.time_begin = item.time_begin
        self.time_end = item.time_end
        self.high = item.high
        self.low = item.low

        self.lst = [kl_unit]  # 本级别每一根单位K线
        kl_unit.klc = self

        self.dir = _dir
        self.fx = FX_TYPE.UNKNOWN
        self.pre = None
        self.next = None

    def test_combine(self, item: CCombine_Item, exclude_included=False):
        if (self.high >= item.high and self.low <= item.low):
            return KLINE_DIR.COMBINE
        if (self.high <= item.high and self.low >= item.low):
            if exclude_included:
                return KLINE_DIR.INCLUDED
            else:
                return KLINE_DIR.COMBINE
        if (self.high > item.high and self.low > item.low):
            return KLINE_DIR.DOWN
        if (self.high < item.high and self.low < item.low):
            return KLINE_DIR.UP
        else:
            raise Exception("combine type unknown")

    def try_add(self, unit_kl, exclude_included=False):
        combine_item = CCombine_Item(unit_kl)
        _dir = self.test_combine(combine_item, exclude_included)
        if _dir == KLINE_DIR.COMBINE:
            self.lst.append(unit_kl)
            unit_kl.klc = self
            if self.dir == KLINE_DIR.UP:
                self.high = max([self.high, combine_item.high])
                self.low = max([self.low, combine_item.low])
            elif self.dir == KLINE_DIR.DOWN:
                self.high = min([self.high, combine_item.high])
                self.low = min([self.low, combine_item.low])
            else:
                raise Exception(f"KLINE_DIR = {self.dir} err!!! must be {KLINE_DIR.UP}/{KLINE_DIR.DOWN}")
            self.time_end = combine_item.time_end
        # 返回UP/DOWN/COMBINE给KL_LIST，设置下一个的方向
        return _dir

    def get_peak_klu(self, is_high):
        # 获取最大值 or 最小值所在klu/bi
        return self.get_high_peak_klu() if is_high else self.get_low_peak_klu()

    @make_cache
    def get_high_peak_klu(self):
        for kl in self.lst:
            if CCombine_Item(kl).high == self.high:
                return kl
        raise Exception("can't find peak...")

    @make_cache
    def get_low_peak_klu(self):
        for kl in self.lst:
            if CCombine_Item(kl).low == self.low:
                return kl
        raise Exception("can't find peak...")

    def update_fx(self, _pre, _next, exclude_included=False):
        self.pre, self.next = _pre, _next
        if exclude_included:
            if _pre.high < self.high and _next.high < self.high and _next.low < self.low:
                self.fx = FX_TYPE.TOP
            elif _next.high > self.high and _pre.low > self.low and _next.low > self.low:
                self.fx = FX_TYPE.BOTTOM
        else:
            if _pre.high < self.high and _next.high < self.high and _pre.low < self.low and _next.low < self.low:
                self.fx = FX_TYPE.TOP
            elif _pre.high > self.high and _next.high > self.high and _pre.low > self.low and _next.low > self.low:
                self.fx = FX_TYPE.BOTTOM

    def check_valid_top_button(self, item2):
        if self.fx == FX_TYPE.TOP:
            assert item2.fx == FX_TYPE.BOTTOM
            return self.high > max([item2.pre.high, item2.next.high])
        elif self.fx == FX_TYPE.BOTTOM:
            assert item2.fx == FX_TYPE.TOP
            return self.low < min([item2.pre.low, item2.next.low])
        else:
            raise Exception("only top/bottom fx can check_valid_top_button")

    def __str__(self):
        return f"{self.time_begin}~{self.time_end} {self.low}->{self.high}"

    def __getitem__(self, n):
        if isinstance(n, int):
            return self.lst[n]
        elif isinstance(n, slice):
            return self.lst[n.start:n.stop:n.step]

    def __len__(self):
        return len(self.lst)

    def __iter__(self):
        for item in self.lst:
            yield item
