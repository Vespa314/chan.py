from typing import Generic, Iterable, List, Optional, Self, TypeVar, Union, overload

from Common.cache import make_cache
from Common.CEnum import FX_TYPE, KLINE_DIR
from Common.ChanException import CChanException, ErrCode
from KLine.KLine_Unit import CKLine_Unit

from .Combine_Item import CCombine_Item

T = TypeVar('T')


class CKLine_Combiner(Generic[T]):
    def __init__(self, kl_unit: T, _dir):
        item = CCombine_Item(kl_unit)
        self.__time_begin = item.time_begin
        self.__time_end = item.time_end
        self.__high = item.high
        self.__low = item.low

        self.__lst: List[T] = [kl_unit]  # 本级别每一根单位K线

        self.__dir = _dir
        self.__fx = FX_TYPE.UNKNOWN
        self.__pre: Optional[Self] = None
        self.__next: Optional[Self] = None

    def clean_cache(self):
        self._memoize_cache = {}

    @property
    def time_begin(self): return self.__time_begin

    @property
    def time_end(self): return self.__time_end

    @property
    def high(self): return self.__high

    @property
    def low(self): return self.__low

    @property
    def lst(self): return self.__lst

    @property
    def dir(self): return self.__dir

    @property
    def fx(self): return self.__fx

    @property
    def pre(self) -> Self:
        assert self.__pre is not None
        return self.__pre

    @property
    def next(self): return self.__next

    def get_next(self) -> Self:
        assert self.next is not None
        return self.next

    def test_combine(self, item: CCombine_Item, exclude_included=False, allow_top_equal=None):
        if (self.high >= item.high and self.low <= item.low):
            return KLINE_DIR.COMBINE
        if (self.high <= item.high and self.low >= item.low):
            if allow_top_equal == 1 and self.high == item.high and self.low > item.low:
                return KLINE_DIR.DOWN
            elif allow_top_equal == -1 and self.low == item.low and self.high < item.high:
                return KLINE_DIR.UP
            return KLINE_DIR.INCLUDED if exclude_included else KLINE_DIR.COMBINE
        if (self.high > item.high and self.low > item.low):
            return KLINE_DIR.DOWN
        if (self.high < item.high and self.low < item.low):
            return KLINE_DIR.UP
        else:
            raise CChanException("combine type unknown", ErrCode.COMBINER_ERR)

    def set_fx(self, fx: FX_TYPE):
        # only for deepcopy
        self.__fx = fx

    def try_add(self, unit_kl: T, exclude_included=False, allow_top_equal=None, skip_update_input=False):
        # allow_top_equal = None普通模式
        # allow_top_equal = 1 被包含，顶部相等不合并
        # allow_top_equal = -1 被包含，底部相等不合并
        combine_item = CCombine_Item(unit_kl)
        _dir = self.test_combine(combine_item, exclude_included, allow_top_equal)
        if _dir == KLINE_DIR.COMBINE:
            self.__lst.append(unit_kl)
            if isinstance(unit_kl, CKLine_Unit) and not skip_update_input:
                unit_kl.set_klc(self)
            if self.dir == KLINE_DIR.UP:
                if combine_item.high != combine_item.low or combine_item.high != self.high:  # 处理一字K线
                    self.__high = max([self.high, combine_item.high])
                    self.__low = max([self.low, combine_item.low])
            elif self.dir == KLINE_DIR.DOWN:
                if combine_item.high != combine_item.low or combine_item.low != self.low:  # 处理一字K线
                    self.__high = min([self.high, combine_item.high])
                    self.__low = min([self.low, combine_item.low])
            else:
                raise CChanException(f"KLINE_DIR = {self.dir} err!!! must be {KLINE_DIR.UP}/{KLINE_DIR.DOWN}", ErrCode.COMBINER_ERR)
            self.__time_end = combine_item.time_end
            self.clean_cache()
        # 返回UP/DOWN/COMBINE给KL_LIST，设置下一个的方向
        return _dir

    def get_peak_klu(self, is_high) -> T:
        # 获取最大值 or 最小值所在klu/bi
        return self.get_high_peak_klu() if is_high else self.get_low_peak_klu()

    @make_cache
    def get_high_peak_klu(self) -> T:
        for kl in self.lst[::-1]:
            if CCombine_Item(kl).high == self.high:
                return kl
        raise CChanException("can't find peak...", ErrCode.COMBINER_ERR)

    @make_cache
    def get_low_peak_klu(self) -> T:
        for kl in self.lst[::-1]:
            if CCombine_Item(kl).low == self.low:
                return kl
        raise CChanException("can't find peak...", ErrCode.COMBINER_ERR)

    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        # allow_top_equal = None普通模式
        # allow_top_equal = 1 被包含，顶部相等不合并
        # allow_top_equal = -1 被包含，底部相等不合并
        self.set_next(_next)
        self.set_pre(_pre)
        _next.set_pre(self)
        if exclude_included:
            if _pre.high < self.high and _next.high <= self.high and _next.low < self.low:
                if allow_top_equal == 1 or _next.high < self.high:
                    self.__fx = FX_TYPE.TOP
            elif _next.high > self.high and _pre.low > self.low and _next.low >= self.low:
                if allow_top_equal == -1 or _next.low > self.low:
                    self.__fx = FX_TYPE.BOTTOM
        elif _pre.high < self.high and _next.high < self.high and _pre.low < self.low and _next.low < self.low:
            self.__fx = FX_TYPE.TOP
        elif _pre.high > self.high and _next.high > self.high and _pre.low > self.low and _next.low > self.low:
            self.__fx = FX_TYPE.BOTTOM
        self.clean_cache()

    def __str__(self):
        return f"{self.time_begin}~{self.time_end} {self.low}->{self.high}"

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> List[T]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[T], T]:
        return self.lst[index]

    def __len__(self):
        return len(self.lst)

    def __iter__(self) -> Iterable[T]:
        yield from self.lst

    def set_pre(self, _pre: Self | None):
        self.__pre = _pre
        self.clean_cache()

    def set_next(self, _next: Self | None):
        self.__next = _next
        self.clean_cache()
