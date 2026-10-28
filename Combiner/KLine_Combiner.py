# -*- coding: utf-8 -*-
"""
K线合并器模块 - 实现缠论的 K 线包含处理逻辑

Java 开发者注意：
- Generic[T] 是 Python 的泛型，类似于 Java 的 <T>。但 Python 泛型在运行时被擦除（和 Java 一样）
- TypeVar('T') 用于声明泛型类型变量，类似于 Java 的 <T>
- Self 是 Python 3.11+ 的类型注解，表示当前类自身
- Optional[Self] 类似于 Java 的 @Nullable Self
- Union[slice, int] 类似于 Java 中没有直接对应，通常用方法重载实现

缠论知识 - K线包含处理：
当相邻两根 K 线出现包含关系（一根完全包含另一根），需要进行合并：
- 合并前需要确定趋势方向
- 上升趋势：取高高（高点=max，低点=max）
- 下降趋势：取低低（高点=min，低点=min）
- 合并后继续与下一根 K 线比较
"""

from typing import Generic, Iterable, List, Optional, Self, TypeVar, Union, overload

from Common.cache import make_cache
from Common.CEnum import FX_TYPE, KLINE_DIR
from Common.ChanException import CChanException, ErrCode
from KLine.KLine_Unit import CKLine_Unit

from .Combine_Item import CCombine_Item

T = TypeVar('T')  # 泛型类型变量，Java 对比：类似于 <T> 声明


class CKLine_Combiner(Generic[T]):
    """
    K线合并器 - 实现缠论中的 K 线包含处理

    这是整个项目中最重要的基类之一，被两个子类继承：
    - CKLine(Combiner[CKLine_Unit])：合并 K 线
    - CEigen(Combiner[CBi])：特征序列元素合并

    功能：
    1. 判断两根 K 线的关系（包含/向上/向下）
    2. 包含处理时合并 K 线的高低点
    3. 检测分形（顶分型/底分型）
    4. 管理前后链表关系

    属性说明：
    - __lst: 合并单元内的原始元素列表
    - __high/__low: 合并后的高低点
    - __dir: 方向（UP/DOWN）
    - __fx: 分型类型（TOP/BOTTOM/UNKNOWN）
    - __pre/__next: 前后链表指针
    """

    def __init__(self, kl_unit: T, _dir):
        """
        初始化合并器
        参数:
            kl_unit: 第一个元素（CKLine_Unit 或 CBi）
            _dir: 初始方向（KLINE_DIR.UP 或 KLINE_DIR.DOWN）
        Python 特性：__开头的变量是私有属性（名称改写为 _ClassName__variable）
        Java 对比：类似于 private 字段
        """
        item = CCombine_Item(kl_unit)
        self.__time_begin = item.time_begin
        self.__time_end = item.time_end
        self.__high = item.high
        self.__low = item.low

        self.__lst: List[T] = [kl_unit]  # 原始元素列表

        self.__dir = _dir
        self.__fx = FX_TYPE.UNKNOWN
        self.__pre: Optional[Self] = None
        self.__next: Optional[Self] = None

    def clean_cache(self):
        """清空缓存字典，使 @make_cache 装饰的方法重新计算"""
        self._memoize_cache = {}

    # ===== 属性访问器（Python 的 @property 装饰器，类似于 Java 的 getter）=====

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
        """获取前一个元素，如果为 None 则断言失败"""
        assert self.__pre is not None
        return self.__pre

    @property
    def next(self): return self.__next

    def get_next(self) -> Self:
        """获取下一个元素，断言不为 None"""
        assert self.next is not None
        return self.next

    def test_combine(self, item: CCombine_Item, exclude_included=False, allow_top_equal=None):
        """
        判断 item 与当前合并元素的关系

        参数:
            item: 待判断的元素
            exclude_included: 是否排除被包含的情况（特征序列合并时使用）
            allow_top_equal: 顶部/底部相等时是否允许合并
                None=普通模式
                1=顶部相等不合并（被包含时）
                -1=底部相等不合并（被包含时）

        返回:
            KLINE_DIR.COMBINE: 需要合并（一根包含另一根）
            KLINE_DIR.INCLUDED: 被包含（仅当 exclude_included=True 时）
            KLINE_DIR.UP: 向上关系
            KLINE_DIR.DOWN: 向下关系

        缠论知识 - 包含关系判断：
        - 如果 self.high >= item.high 且 self.low <= item.low：self 包含 item → COMBINE
        - 如果 self.high <= item.high 且 self.low >= item.low：item 包含 self → COMBINE/INCLUDED
        - 如果 self.high > item.high 且 self.low > item.low：向下趋势 → DOWN
        - 如果 self.high < item.high 且 self.low < item.low：向上趋势 → UP
        """
        # 情况1：self 完全包含 item（self 高更高，低更低）
        if (self.high >= item.high and self.low <= item.low):
            return KLINE_DIR.COMBINE

        # 情况2：item 完全包含 self
        if (self.high <= item.high and self.low >= item.low):
            # 处理顶部/底部相等时的特殊情况
            if allow_top_equal == 1 and self.high == item.high and self.low > item.low:
                return KLINE_DIR.DOWN  # 顶部相等，视作向下
            elif allow_top_equal == -1 and self.low == item.low and self.high < item.high:
                return KLINE_DIR.UP  # 底部相等，视作向上
            return KLINE_DIR.INCLUDED if exclude_included else KLINE_DIR.COMBINE

        # 情况3：self 整体在 item 下方 → 向下关系
        if (self.high > item.high and self.low > item.low):
            return KLINE_DIR.DOWN

        # 情况4：self 整体在 item 上方 → 向上关系
        if (self.high < item.high and self.low < item.low):
            return KLINE_DIR.UP

        # 走到这里说明逻辑异常（如 self.high > item.high 但 self.low < item.low）
        # 这种情况理论上不会出现，因为前面已经处理了包含关系
        raise CChanException("combine type unknown", ErrCode.COMBINER_ERR)

    def set_fx(self, fx: FX_TYPE):
        """设置分型类型（仅用于 deepcopy 后恢复）"""
        self.__fx = fx

    def try_add(self, unit_kl: T, exclude_included=False, allow_top_equal=None, skip_update_input=False):
        """
        尝试将新元素加入合并

        参数:
            unit_kl: 待加入的元素
            exclude_included: 是否排除被包含情况
            allow_top_equal: 顶部/底部相等时的处理
            skip_update_input: 跳过更新元素的 klc 引用（deepcopy 时使用）

        返回:
            KLINE_DIR.COMBINE: 合并成功
            KLINE_DIR.UP/DOWN: 未合并，返回方向关系

        缠论知识 - 合并规则：
        当 test_combine 返回 COMBINE 时：
        - 上升趋势（dir==UP）：高取 max，低取 max（高高）
        - 下降趋势（dir==DOWN）：高取 min，低取 min（低低）
        - 时间范围扩展到新元素的时间
        - K线的时间顺序不变（先出现的在前）
        """
        combine_item = CCombine_Item(unit_kl)
        _dir = self.test_combine(combine_item, exclude_included, allow_top_equal)

        if _dir == KLINE_DIR.COMBINE:
            # 需要合并
            self.__lst.append(unit_kl)
            if isinstance(unit_kl, CKLine_Unit) and not skip_update_input:
                unit_kl.set_klc(self)  # 设置反向引用：让 K线单元知道自己属于哪个合并K线

            if self.dir == KLINE_DIR.UP:
                # 上升趋势：高高（取高点的高者，低点的高者）
                # 处理一字K线（high==low）：一字K线不改变高低点
                if combine_item.high != combine_item.low or combine_item.high != self.high:
                    self.__high = max([self.high, combine_item.high])  # 高点取最大值
                    self.__low = max([self.low, combine_item.low])    # 低点取最大值
            elif self.dir == KLINE_DIR.DOWN:
                # 下降趋势：低低（取高点的低者，低点的低者）
                if combine_item.high != combine_item.low or combine_item.low != self.low:
                    self.__high = min([self.high, combine_item.high])  # 高点取最小值
                    self.__low = min([self.low, combine_item.low])    # 低点取最小值
            else:
                raise CChanException(f"KLINE_DIR = {self.dir} err!!!", ErrCode.COMBINER_ERR)

            self.__time_end = combine_item.time_end
            self.clean_cache()  # 合并后缓存失效，因为高低点可能变了

        return _dir  # 返回方向给调用方，用于设置下一个元素的方向

    def get_peak_klu(self, is_high) -> T:
        """
        获取最大值或最小值所在的原始元素（klu 或 bi）
        参数:
            is_high: True=找最高点，False=找最低点
        返回:
            极值所在的原始元素
        """
        return self.get_high_peak_klu() if is_high else self.get_low_peak_klu()

    @make_cache
    def get_high_peak_klu(self) -> T:
        """
        获取最高点所在的原始元素（带缓存）
        从后往前找，确保找到的是最新的极值点
        Python 语法：self.lst[::-1] 是切片反转列表，类似于 Java 的 Collections.reverse()
        """
        for kl in self.lst[::-1]:
            if CCombine_Item(kl).high == self.high:
                return kl
        raise CChanException("can't find peak...", ErrCode.COMBINER_ERR)

    @make_cache
    def get_low_peak_klu(self) -> T:
        """
        获取最低点所在的原始元素（带缓存）
        从后往前找，确保找到的是最新的极值点
        """
        for kl in self.lst[::-1]:
            if CCombine_Item(kl).low == self.low:
                return kl
        raise CChanException("can't find peak...", ErrCode.COMBINER_ERR)

    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        """
        检测分形（顶分型/底分型）

        参数:
            _pre: 前一个元素
            _next: 后一个元素
            exclude_included: 是否排除被包含情况
            allow_top_equal: 顶部/底部相等时的处理

        缠论知识 - 分形判断：
        - 顶分型：中间元素的高点最高，且中间元素的低点也最高
        - 底分型：中间元素的低点最低，且中间元素的高点也最低

        判断公式（普通模式）：
        - 顶分型：pre.high < self.high 且 next.high < self.high
                  且 pre.low < self.low 且 next.low < self.low
        - 底分型：pre.high > self.high 且 next.high > self.high
                  且 pre.low > self.low 且 next.low > self.low
        """
        # 设置链表关系
        self.set_next(_next)
        self.set_pre(_pre)
        _next.set_pre(self)

        if exclude_included:
            # 特征序列模式的分型判断（针对虚段）
            if _pre.high < self.high and _next.high <= self.high and _next.low < self.low:
                if allow_top_equal == 1 or _next.high < self.high:
                    self.__fx = FX_TYPE.TOP
            elif _next.high > self.high and _pre.low > self.low and _next.low >= self.low:
                if allow_top_equal == -1 or _next.low > self.low:
                    self.__fx = FX_TYPE.BOTTOM
        else:
            # 普通K线分型判断
            if _pre.high < self.high and _next.high < self.high and _pre.low < self.low and _next.low < self.low:
                self.__fx = FX_TYPE.TOP    # 顶分型：中间高最高，中间低也最高
            elif _pre.high > self.high and _next.high > self.high and _pre.low > self.low and _next.low > self.low:
                self.__fx = FX_TYPE.BOTTOM  # 底分型：中间低最低，中间高也最低

        self.clean_cache()

    def __str__(self):
        """字符串表示，格式如 '2024/01/01~2024/01/05 10.0->12.0'"""
        return f"{self.time_begin}~{self.time_end} {self.low}->{self.high}"

    # ===== 索引和迭代支持 =====
    # Python 特性：__getitem__ 方法支持 [] 索引操作，类似于 Java 中实现 List 接口
    # __len__ 支持 len() 函数，__iter__ 支持 for...in 循环

    @overload
    def __getitem__(self, index: int) -> T: ...
    # Python 的 @overload 装饰器仅用于类型提示，不影响运行时行为
    # Java 对比：Java 直接写多个重载方法

    @overload
    def __getitem__(self, index: slice) -> List[T]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[T], T]:
        """
        支持 [] 索引访问
        Python 语法：Union[slice, int] 表示参数可以是 slice 或 int 类型
        """
        return self.lst[index]

    def __len__(self):
        """支持 len() 函数"""
        return len(self.lst)

    def __iter__(self) -> Iterable[T]:
        """支持 for...in 循环（Python 语法，类似于 Java 的 Iterable.iterator()）"""
        yield from self.lst
        # Python 语法：yield from 是生成器委托，类似于 Java 中迭代器的 flatMap

    def set_pre(self, _pre: Self | None):
        """设置前一个元素的引用，并清空缓存"""
        self.__pre = _pre
        self.clean_cache()

    def set_next(self, _next: Self | None):
        """设置后一个元素的引用，并清空缓存"""
        self.__next = _next
        self.clean_cache()