# -*- coding: utf-8 -*-
"""
中枢模块 - 表示缠论中的"中枢"，由至少三笔重叠构成

Java 开发者注意：
- Generic[LINE_TYPE] 是 Python 泛型，类似于 Java 的 <LINE_TYPE>
- Optional[T] 类似于 Java 的 @Nullable T
- Python 的 := (海象运算符) 在表达式中赋值，Java 没有直接对应
- Python 的 min/max 可以接受生成器表达式，类似于 Java 的 Stream.min/max
"""

from typing import Generic, List, Optional, TypeVar

from Bi.Bi import CBi
from BuySellPoint.BSPointConfig import CPointConfig
from Common.ChanException import CChanException, ErrCode
from Common.func_util import has_overlap
from KLine.KLine_Unit import CKLine_Unit
from Seg.Seg import CSeg

LINE_TYPE = TypeVar('LINE_TYPE', CBi, "CSeg")


class CZS(Generic[LINE_TYPE]):
    """
    中枢 - 由至少三笔（或三段）的重叠区间构成

    缠论知识 - 中枢的定义：
    中枢由连续的三笔（或三段）构成，取这三笔重叠的区间。
    中枢区间 = [max(三笔的_low), min(三笔的_high)]

    中枢是缠论中最重要的概念之一：
    - 中枢是趋势和盘整的区分标准
    - 中枢的进入笔（bi_in）和离开笔（bi_out）用于判断第三类买卖点
    - 中枢的移动和扩展用于判断趋势的延续

    属性说明：
    - begin/end: 中枢的起始/结束K线单元
    - low/high: 中枢的区间范围
    - mid: 中枢的中点
    - peak_low/peak_high: 中枢涉及笔的极值（大于中枢区间）
    - begin_bi/end_bi: 中枢的第一笔/最后一笔
    - bi_in: 进入中枢的笔（中枢第一笔的前一笔）
    - bi_out: 离开中枢的笔（中枢最后一笔的后一笔）
    - bi_lst: 中枢内部的笔列表
    - sub_zs_lst: 子中枢列表（合并后的历史中枢）
    """

    def __init__(self, lst: Optional[List[LINE_TYPE]], is_sure=True):
        """
        初始化中枢

        参数:
            lst: 构成中枢的笔列表（至少3笔），None 表示用于拷贝
            is_sure: 是否确认

        中枢区间计算：
        - low = max(各笔的_low)  ← 中枢下沿
        - high = min(各笔的_high) ← 中枢上沿
        - mid = (low + high) / 2  ← 中枢中位价
        """
        self.__is_sure = is_sure
        self.__sub_zs_lst: List[CZS] = []

        if lst is None:
            return

        self.__begin: CKLine_Unit = lst[0].get_begin_klu()
        self.__begin_bi: LINE_TYPE = lst[0]

        self.update_zs_range(lst)

        self.__peak_high = float("-inf")
        self.__peak_low = float("inf")
        for item in lst:
            self.update_zs_end(item)

        self.__bi_in: Optional[LINE_TYPE] = None  # 进中枢那一笔
        self.__bi_out: Optional[LINE_TYPE] = None  # 出中枢那一笔

        self.__bi_lst: List[LINE_TYPE] = []  # begin_bi~end_bi之间的笔

    def clean_cache(self):
        self._memoize_cache = {}

    # ===== 属性访问器 =====
    @property
    def is_sure(self): return self.__is_sure

    @property
    def sub_zs_lst(self): return self.__sub_zs_lst

    @property
    def begin(self): return self.__begin

    @property
    def begin_bi(self): return self.__begin_bi

    @property
    def low(self): return self.__low

    @property
    def high(self): return self.__high

    @property
    def mid(self): return self.__mid

    @property
    def end(self): return self.__end

    @property
    def end_bi(self): return self.__end_bi

    @property
    def peak_high(self): return self.__peak_high

    @property
    def peak_low(self): return self.__peak_low

    @property
    def bi_in(self): return self.__bi_in

    @property
    def bi_out(self): return self.__bi_out

    @property
    def bi_lst(self): return self.__bi_lst

    def update_zs_range(self, lst):
        """
        更新中枢区间

        参数:
            lst: 构成中枢的笔列表

        中枢区间 = [max(各笔的_low), min(各笔的_high)]
        - low: 取各笔低点的最大值（中枢下沿）
        - high: 取各笔高点的最小值（中枢上沿）
        """
        self.__low: float = max(bi._low() for bi in lst)
        self.__high: float = min(bi._high() for bi in lst)
        self.__mid: float = (self.__low + self.__high) / 2
        self.clean_cache()

    def is_one_bi_zs(self):
        """
        判断是否是一笔中枢

        一笔中枢：只有一笔的中枢（begin_bi == end_bi）
        用于处理中枢扩展时的特殊情况。
        """
        assert self.end_bi is not None
        return self.begin_bi.idx == self.end_bi.idx

    def update_zs_end(self, item):
        """
        更新中枢的结束位置和极值

        参数:
            item: 新加入中枢的笔

        同时更新：
        - end: 中枢结束K线
        - end_bi: 中枢结束笔
        - peak_low/peak_high: 中枢极值（所有笔的全局最低/最高）
        """
        self.__end: CKLine_Unit = item.get_end_klu()
        self.__end_bi: CBi = item
        if item._low() < self.peak_low:
            self.__peak_low = item._low()
        if item._high() > self.peak_high:
            self.__peak_high = item._high()
        self.clean_cache()

    def __str__(self):
        """字符串表示，格式如 '0->5(2->3,4->5)' 表示中枢合并历史"""
        _str = f"{self.begin_bi.idx}->{self.end_bi.idx}"
        if _str2 := ",".join([str(sub_zs) for sub_zs in self.sub_zs_lst]):
            # Python 语法：:= 海象运算符，在表达式中赋值
            # Java 对比：需要先计算再判断
            return f"{_str}({_str2})"
        else:
            return _str

    def combine(self, zs2: 'CZS', combine_mode) -> bool:
        """
        尝试合并两个中枢

        参数:
            zs2: 待合并的中枢（后一个中枢）
            combine_mode: 合并模式
              - "zs": 中枢区间有重叠才合并
              - "peak": 中枢极值区间有重叠就合并

        返回:
            True 如果合并成功

        缠论知识 - 中枢合并：
        当两个相邻中枢的区间有重叠时，它们合并为一个更大的中枢。
        合并后的中枢区间取两个中枢的并集。

        合并条件：
        1. zs2 不能是一笔中枢
        2. 两个中枢必须在同一线段内
        3. 区间有重叠（根据 combine_mode 判断）
        """
        if zs2.is_one_bi_zs():
            return False
        if self.begin_bi.seg_idx != zs2.begin_bi.seg_idx:
            return False
        if combine_mode == 'zs':
            if not has_overlap(self.low, self.high, zs2.low, zs2.high, equal=True):
                return False
            self.do_combine(zs2)
            return True
        elif combine_mode == 'peak':
            if has_overlap(self.peak_low, self.peak_high, zs2.peak_low, zs2.peak_high):
                self.do_combine(zs2)
                return True
            else:
                return False
        else:
            raise CChanException(f"{combine_mode} is unsupport zs conbine mode", ErrCode.PARA_ERROR)

    def do_combine(self, zs2: 'CZS'):
        """
        执行中枢合并操作

        合并后的中枢：
        - 区间扩展为两个中枢的并集
        - 极值扩展为两个中枢极值的并集
        - 结束点更新为 zs2 的结束点
        - bi_out 更新为 zs2 的 bi_out
        """
        if len(self.sub_zs_lst) == 0:
            self.__sub_zs_lst.append(self.make_copy())  # 保存原中枢
        self.__sub_zs_lst.append(zs2)

        self.__low = min([self.low, zs2.low])
        self.__high = max([self.high, zs2.high])
        self.__peak_low = min([self.peak_low, zs2.peak_low])
        self.__peak_high = max([self.peak_high, zs2.peak_high])
        self.__end = zs2.end
        self.__bi_out = zs2.bi_out
        self.__end_bi = zs2.end_bi
        self.clean_cache()

    def try_add_to_end(self, item):
        """
        尝试将一笔添加到中枢末尾

        参数:
            item: 待添加的笔

        返回:
            True 如果添加成功

        条件：item 必须与中枢区间有重叠
        如果是一笔中枢，需要更新中枢区间。
        """
        if not self.in_range(item):
            return False
        if self.is_one_bi_zs():
            self.update_zs_range([self.begin_bi, item])
        self.update_zs_end(item)
        return True

    def in_range(self, item):
        """
        判断一笔是否在中枢区间内

        判断标准：item 的区间 [low, high] 是否与中枢区间 [low, high] 有重叠
        """
        return has_overlap(self.low, self.high, item._low(), item._high())

    def is_inside(self, seg: CSeg):
        """
        判断中枢是否在线段内部

        判断标准：中枢的起始笔是否在线段的笔范围内
        """
        return seg.start_bi.idx <= self.begin_bi.idx <= seg.end_bi.idx

    def is_divergence(self, config: CPointConfig, out_bi=None):
        """
        判断中枢是否发生背驰

        参数:
            config: 买卖点配置
            out_bi: 离开中枢的笔（如果为 None，使用 bi_out）

        返回:
            (是否背驰, 背驰率)

        缠论知识 - 中枢背驰：
        中枢背驰 = 离开中枢的笔力度 < 进入中枢的笔力度
        力度通过 MACD 指标衡量（由 config.macd_algo 决定）。

        背驰率 = 离开笔 MACD 指标 / 进入笔 MACD 指标
        背驰率 < divergence_rate 时，认为发生背驰。
        divergence_rate > 100 时，"保送"（无条件视为背驰）。

        注意：
        - 进入笔用正向计算（is_reverse=False）
        - 离开笔用反向计算（is_reverse=True）
        """
        if not self.end_bi_break(out_bi):  # 最后一笔必须突破中枢
            return False, None
        in_metric = self.get_bi_in().cal_macd_metric(config.macd_algo, is_reverse=False)
        if out_bi is None:
            out_metric = self.get_bi_out().cal_macd_metric(config.macd_algo, is_reverse=True)
        else:
            out_metric = out_bi.cal_macd_metric(config.macd_algo, is_reverse=True)

        if config.divergence_rate > 100:  # 保送：无条件视为背驰
            return True, out_metric/in_metric
        else:
            return out_metric <= config.divergence_rate*in_metric, out_metric/in_metric

    def init_from_zs(self, zs: 'CZS'):
        """
        从另一个中枢复制属性（用于拷贝）
        """
        self.__begin = zs.begin
        self.__end = zs.end
        self.__low = zs.low
        self.__high = zs.high
        self.__peak_high = zs.peak_high
        self.__peak_low = zs.peak_low
        self.__begin_bi = zs.begin_bi
        self.__end_bi = zs.end_bi
        self.__bi_in = zs.bi_in
        self.__bi_out = zs.bi_out

    def make_copy(self) -> 'CZS':
        """
        创建中枢的拷贝（用于保存合并前的历史中枢）

        Python 特性：通过 lst=None 创建空中枢，然后用 init_from_zs 复制属性
        Java 对比：类似于 Cloneable 接口 + clone() 方法
        """
        copy = CZS(lst=None, is_sure=self.is_sure)
        copy.init_from_zs(zs=self)
        return copy

    def end_bi_break(self, end_bi=None) -> bool:
        """
        判断离开笔是否突破了中枢区间

        参数:
            end_bi: 离开笔（如果为 None，使用 bi_out）

        返回:
            True 如果离开笔突破了中枢

        突破条件：
        - 下降笔：笔的低点 < 中枢的低点
        - 上升笔：笔的高点 > 中枢的高点
        """
        if end_bi is None:
            end_bi = self.get_bi_out()
        assert end_bi is not None
        return (end_bi.is_down() and end_bi._low() < self.low) or \
            (end_bi.is_up() and end_bi._high() > self.high)

    def out_bi_is_peak(self, end_bi_idx: int):
        """
        判断离开笔是否是中枢之后的最极值笔

        参数:
            end_bi_idx: 线段的结束笔索引

        返回:
            (是否是最极值, 与最近一笔的差距比例)

        查找逻辑：
        在中枢内部的笔中，找离结束笔最近的一笔，
        判断离开笔是否比中枢内的笔都更极端。
        """
        assert len(self.bi_lst) > 0
        if self.bi_out is None:
            return False, None
        peak_rate = float("inf")
        for bi in self.bi_lst:
            if bi.idx > end_bi_idx:
                break
            if (self.bi_out.is_down() and bi._low() < self.bi_out._low()) or \
               (self.bi_out.is_up() and bi._high() > self.bi_out._high()):
                return False, None
            r = abs(bi.get_end_val()-self.bi_out.get_end_val())/self.bi_out.get_end_val()
            if r < peak_rate:
                peak_rate = r
        return True, peak_rate

    def get_bi_in(self) -> LINE_TYPE:
        assert self.bi_in is not None
        return self.bi_in

    def get_bi_out(self) -> LINE_TYPE:
        assert self.__bi_out is not None
        return self.__bi_out

    def set_bi_in(self, bi):
        self.__bi_in = bi
        self.clean_cache()

    def set_bi_out(self, bi):
        self.__bi_out = bi
        self.clean_cache()

    def set_bi_lst(self, bi_lst):
        self.__bi_lst = bi_lst
        self.clean_cache()