# -*- coding: utf-8 -*-
"""
线段模块 - 表示缠论中的"线段"，由多笔构成

Java 开发者注意：
- Generic[LINE_TYPE] 是 Python 泛型，类似于 Java 的 <LINE_TYPE>
- Self 是 Python 3.11+ 的类型注解，表示当前类自身
- Optional[Self] 类似于 Java 的 @Nullable Self
- Python 的 assert 默认启用，类似于 Java 的 assert 但需要 -ea 参数
- Python 的生成器表达式 (zs for zs in ... if ...) 类似于 Java 的 Stream.filter()
"""

from typing import Generic, List, Optional, Self, TypeVar

from Bi.Bi import CBi
from Common.CEnum import BI_DIR, MACD_ALGO, TREND_LINE_SIDE
from Common.ChanException import CChanException, ErrCode
from KLine.KLine_Unit import CKLine_Unit
from Math.TrendLine import CTrendLine

from .EigenFX import CEigenFX

LINE_TYPE = TypeVar('LINE_TYPE', CBi, "CSeg")
# Python 语法：TypeVar 可以有 bound 约束，这里用 CBi | "CSeg" 表示两个可能的类型
# Java 对比：<T extends CBi | CSeg>，但 Java 泛型不支持联合类型


class CSeg(Generic[LINE_TYPE]):
    """
    线段 - 由至少三笔重叠构成

    缠论知识 - 线段的定义：
    线段由至少三笔构成，且必须有重叠区间。
    线段是比笔更高一级的走势结构，用于构建中枢。

    两个层次的线段：
    1. 笔的线段（LINE_TYPE = CBi）：由笔构成
    2. 线段的线段（LINE_TYPE = CSeg[CBi]）：由线段构成，更高层次

    属性说明：
    - idx: 线段索引
    - start_bi/end_bi: 起始/结束笔（或线段）
    - is_sure: 是否确认
    - dir: 方向（UP/DOWN）
    - zs_lst: 线段内的中枢列表
    - eigen_fx: 特征序列分型（仅特征序列法使用）
    - bi_list: 线段包含的笔列表
    - support_trend_line/resistance_trend_line: 支撑/阻力趋势线
    - ele_inside_is_sure: 线段内部元素是否已确认
    """

    def __init__(self, idx: int, start_bi: LINE_TYPE, end_bi: LINE_TYPE, is_sure=True, seg_dir=None, reason="normal"):
        """
        初始化线段

        参数:
            idx: 线段索引
            start_bi: 起始笔
            end_bi: 结束笔
            is_sure: 是否确认
            seg_dir: 线段方向（如果为None，则从end_bi推断）
            reason: 创建原因（用于调试追踪）

        约束：
        - 确认线段：start_bi 和 end_bi 方向必须一致
        - 线段长度（笔数）必须 >= 3
        """
        assert start_bi.idx == 0 or start_bi.dir == end_bi.dir or not is_sure, \
            f"{start_bi.idx} {end_bi.idx} {start_bi.dir} {end_bi.dir}"
        self.idx = idx
        self.start_bi = start_bi
        self.end_bi = end_bi
        self.is_sure = is_sure
        self.used_to_be_sure = is_sure
        self.dir = end_bi.dir if seg_dir is None else seg_dir

        from ZS.ZS import CZS
        self.zs_lst: List[CZS[LINE_TYPE]] = []

        self.eigen_fx: Optional[CEigenFX] = None
        self.seg_idx = None  # 线段的线段使用
        self.parent_seg: Optional[CSeg] = None  # 属于哪个线段
        self.pre: Optional[Self] = None
        self.next: Optional[Self] = None

        from BuySellPoint.BS_Point import CBS_Point
        self.bsp: Optional[CBS_Point] = None  # 尾部是不是买卖点

        self.bi_list: List[LINE_TYPE] = []  # 仅通过 self.update_bi_list 来更新
        self.reason = reason
        self.support_trend_line = None
        self.resistance_trend_line = None
        if end_bi.idx - start_bi.idx < 2:
            self.is_sure = False  # 笔数不足3笔，不能确认
        self.check()

        self.ele_inside_is_sure = False

    def set_seg_idx(self, idx):
        """设置线段的线段索引"""
        self.seg_idx = idx

    def check(self):
        """
        校验线段的合法性
        检查：
        - 下降线段：起始点 > 结束点
        - 上升线段：起始点 < 结束点
        - 线段长度 >= 3笔
        """
        if not self.is_sure:
            return
        if self.is_down():
            if self.start_bi.get_begin_val() < self.end_bi.get_end_val():
                raise CChanException(f"下降线段起始点应该高于结束点! idx={self.idx}", ErrCode.SEG_END_VALUE_ERR)
        elif self.start_bi.get_begin_val() > self.end_bi.get_end_val():
            raise CChanException(f"上升线段起始点应该低于结束点! idx={self.idx}", ErrCode.SEG_END_VALUE_ERR)
        if self.end_bi.idx - self.start_bi.idx < 2:
            raise CChanException(f"线段({self.start_bi.idx}-{self.end_bi.idx})长度不能小于2! idx={self.idx}", ErrCode.SEG_LEN_ERR)

    def __str__(self):
        """字符串表示，格式如 '0->5: BI_DIR.UP  True'"""
        return f"{self.start_bi.idx}->{self.end_bi.idx}: {self.dir}  {self.is_sure}"

    def add_zs(self, zs):
        """添加中枢到线段（中枢是反序加入的，所以插到列表前面）"""
        self.zs_lst = [zs] + self.zs_lst

    def cal_klu_slope(self):
        """
        计算线段基于原始K线的斜率
        斜率 = (结束值 - 起始值) / (K线数量) / 起始值
        用于衡量线段的力度
        """
        assert self.end_bi.idx >= self.start_bi.idx
        return (self.get_end_val()-self.get_begin_val())/(self.get_end_klu().idx-self.get_begin_klu().idx)/self.get_begin_val()

    def cal_amp(self):
        """
        计算线段的振幅
        振幅 = (结束值 - 起始值) / 起始值
        """
        return (self.get_end_val()-self.get_begin_val())/self.get_begin_val()

    def cal_bi_cnt(self):
        """线段包含的笔数量"""
        return self.end_bi.idx-self.start_bi.idx+1

    def clear_zs_lst(self):
        """清空中枢列表"""
        self.zs_lst = []

    def _low(self):
        """
        线段的最低点
        - 下降线段：结束笔的最低点
        - 上升线段：起始笔的最低点
        """
        return self.end_bi.get_end_klu().low if self.is_down() else self.start_bi.get_begin_klu().low

    def _high(self):
        """
        线段的最高点
        - 上升线段：结束笔的最高点
        - 下降线段：起始笔的最高点
        """
        return self.end_bi.get_end_klu().high if self.is_up() else self.start_bi.get_begin_klu().high

    def is_down(self):
        return self.dir == BI_DIR.DOWN

    def is_up(self):
        return self.dir == BI_DIR.UP

    def get_end_val(self):
        return self.end_bi.get_end_val()

    def get_begin_val(self):
        return self.start_bi.get_begin_val()

    @property
    def is_used_to_be_sure(self) -> bool:
        """线段是否曾经被确认过（包括当前确认状态）"""
        return self.is_sure or self.used_to_be_sure

    def amp(self):
        """线段振幅（绝对值）"""
        return abs(self.get_end_val() - self.get_begin_val())

    def get_end_klu(self) -> CKLine_Unit:
        """获取线段结束点所在的原始K线"""
        return self.end_bi.get_end_klu()

    def get_begin_klu(self) -> CKLine_Unit:
        """获取线段起始点所在的原始K线"""
        return self.start_bi.get_begin_klu()

    def get_klu_cnt(self):
        """线段包含的原始K线数量"""
        return self.get_end_klu().idx - self.get_begin_klu().idx + 1

    def cal_macd_metric(self, macd_algo, is_reverse):
        """
        计算线段的 MACD 背驰指标
        线段只支持斜率法（SLOPE）和振幅法（AMP）
        """
        if macd_algo == MACD_ALGO.SLOPE:
            return self.Cal_MACD_slope()
        elif macd_algo == MACD_ALGO.AMP:
            return self.Cal_MACD_amp()
        else:
            raise CChanException(f"unsupport macd_algo={macd_algo} of Seg, should be one of slope/amp", ErrCode.PARA_ERROR)

    def Cal_MACD_slope(self):
        """
        计算线段的斜率指标
        上升线段：(结束高点 - 起始低点) / 结束高点 / K线数量
        下降线段：(起始高点 - 结束低点) / 起始高点 / K线数量
        """
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_up():
            return (end_klu.high - begin_klu.low)/end_klu.high/(end_klu.idx - begin_klu.idx + 1)
        else:
            return (begin_klu.high - end_klu.low)/begin_klu.high/(end_klu.idx - begin_klu.idx + 1)

    def Cal_MACD_amp(self):
        """
        计算线段的振幅指标
        下降线段：(起始高点 - 结束低点) / 起始高点
        上升线段：(结束高点 - 起始低点) / 起始低点
        """
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_down():
            return (begin_klu.high-end_klu.low)/begin_klu.high
        else:
            return (end_klu.high-begin_klu.low)/begin_klu.low

    def update_bi_list(self, bi_lst, idx1, idx2):
        """
        更新线段包含的笔列表

        参数:
            bi_lst: 完整的笔列表
            idx1: 起始笔索引
            idx2: 结束笔索引

        设置每笔的 parent_seg 引用，并计算趋势线（如果笔数>=3）
        """
        for bi_idx in range(idx1, idx2+1):
            bi_lst[bi_idx].parent_seg = self
            self.bi_list.append(bi_lst[bi_idx])
        if len(self.bi_list) >= 3:
            self.support_trend_line = CTrendLine(self.bi_list, TREND_LINE_SIDE.INSIDE)
            self.resistance_trend_line = CTrendLine(self.bi_list, TREND_LINE_SIDE.OUTSIDE)

    def get_first_multi_bi_zs(self):
        """
        获取第一个多笔中枢（非一笔中枢）

        Python 语法：next(iter, None) 获取迭代器的第一个元素，空则返回 None
        Java 对比：类似于 stream.findFirst().orElse(null)
        """
        return next((zs for zs in self.zs_lst if not zs.is_one_bi_zs()), None)

    def get_multi_bi_zs_lst(self):
        """
        获取所有多笔中枢列表

        Python 语法：列表推导式 [zs for zs in ... if ...]
        Java 对比：类似于 stream.filter().collect(Collectors.toList())
        """
        return [zs for zs in self.zs_lst if not zs.is_one_bi_zs()]

    def get_final_multi_bi_zs(self):
        """
        获取最后一个多笔中枢（从后往前找）

        缠论知识：最后一个中枢用于判断第三类买卖点
        """
        zs_idx = len(self.zs_lst) - 1
        while zs_idx >= 0:
            zs = self.zs_lst[zs_idx]
            if not zs.is_one_bi_zs():
                return zs
            zs_idx -= 1
        return None

    def get_multi_bi_zs_cnt(self):
        """
        获取多笔中枢的数量

        Python 语法：sum(condition for item in iterable)
        利用了 True/False 在算术运算中等于 1/0 的特性
        Java 对比：stream.filter().count()
        """
        return sum(not zs.is_one_bi_zs() for zs in self.zs_lst)