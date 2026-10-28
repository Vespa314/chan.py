# -*- coding: utf-8 -*-
"""
合并K线模块 - 经包含处理后的 K 线，同时也是 CKLine_Combiner 的子类

Java 开发者注意：
- CKLine(CKLine_Combiner[CKLine_Unit]) 是 Python 泛型继承语法
  Java 对比：class CKLine extends CKLine_Combiner<CKLine_Unit>
- super(CKLine, self).__init__() 是 Python 2 兼容的 super 写法
  Python 3 可用 super().__init__()，Java 对比：super(arg)
- 生成器方法 yield 是 Python 特有的，Java 没有直接对应
  （Java 需要用 Iterator 接口或 Stream 实现）
"""

from Combiner.KLine_Combiner import CKLine_Combiner
from Common.CEnum import FX_CHECK_METHOD, FX_TYPE, KLINE_DIR
from Common.ChanException import CChanException, ErrCode
from Common.func_util import has_overlap
from KLine.KLine_Unit import CKLine_Unit


class CKLine(CKLine_Combiner[CKLine_Unit]):
    """
    合并后的K线 - 继承 KLine 合并器的所有功能

    缠论知识 - 合并K线：
    经过包含处理后，多根有包含关系的原始K线被合并成一根"合并K线"。
    合并K线是形成笔的基础单元——顶底分型在合并K线上检测。

    泛型参数：CKLine_Combiner[CKLine_Unit] 表示泛型类型 T = CKLine_Unit
    属性说明：
    - idx: 合并K线在列表中的索引
    - kl_type: K线级别类型（日线/30分钟/5分钟等）
    - lst: 继承自父类，包含被合并的原始K线单元列表
    """

    def __init__(self, kl_unit: CKLine_Unit, idx, _dir=KLINE_DIR.UP):
        """
        初始化合并K线
        参数:
            kl_unit: 第一根原始K线单元
            idx: 合并K线的索引
            _dir: 初始方向，默认向上（UP）
        Python 语法：super(CKLine, self).__init__(kl_unit, _dir) 是显式调用父类构造
        Java 对比：super(kl_unit, _dir)
        """
        super(CKLine, self).__init__(kl_unit, _dir)
        self.idx: int = idx
        self.kl_type = kl_unit.kl_type
        kl_unit.set_klc(self)  # 建立反向引用

    def __str__(self):
        """
        字符串表示，包含分型标记
        Python 特性：__str__ 类似于 Java 的 toString()
        格式：序号+分型标记:时间范围(级别|包含K线数) low=xxx high=xxx
        分型标记：^ 表示顶分型，_ 表示底分型
        """
        fx_token = ""
        if self.fx == FX_TYPE.TOP:
            fx_token = "^"
        elif self.fx == FX_TYPE.BOTTOM:
            fx_token = "_"
        return f"{self.idx}th{fx_token}:{self.time_begin}~{self.time_end}({self.kl_type}|{len(self.lst)}) low={self.low} high={self.high}"

    def GetSubKLC(self):
        """
        获取所有子级别合并K线（去重）

        返回:
            子级别合并K线的生成器迭代器

        使用场景：多级别递归时，获取当前合并K线对应的所有子级别合并K线

        注意：相邻两个父KLC的子KLC可能存在重复，因为子级别K线合并时
              可能正好跨过了父KLC的时间边界，所以需要去重处理

        Python 语法：yield 是生成器关键字，每次调用产出下一个元素
        Java 对比：没有直接语法对应，需要实现 Iterator 接口或使用 Stream
        """
        last_klc = None
        for klu in self.lst:  # 遍历所有被合并的原始K线
            for sub_klu in klu.get_children():  # 获取每根原始K线的子级别K线
                if sub_klu.klc != last_klc:  # 去重：跳过连续相同的KLC
                    last_klc = sub_klu.klc
                    yield sub_klu.klc

    def get_klu_max_high(self) -> float:
        """
        获取所有原始K线中的最高点
        Python 语法：生成器表达式 max(x.high for x in self.lst)
        Java 对比：类似于 stream().mapToDouble().max().orElse(0)
        """
        return max(x.high for x in self.lst)

    def get_klu_min_low(self) -> float:
        """
        获取所有原始K线中的最低点
        """
        return min(x.low for x in self.lst)

    def has_gap_with_next(self) -> bool:
        """
        判断当前合并K线与下一根合并K线之间是否有跳空缺口

        返回:
            True 如果有缺口（两根K线的价格区间不重叠）

        缠论知识 - 跳空缺口：
        两根K线之间如果价格区间不重叠，即为跳空。
        跳空在特征序列法中用于判断是否需要特殊处理（线段破坏的第二种情况）。

        has_overlap 的 equal=True 参数表示：边界相等也算重叠（无缺口）
        """
        assert self.next is not None
        return not has_overlap(self.get_klu_min_low(), self.get_klu_max_high(), self.next.get_klu_min_low(), self.next.get_klu_max_high(), equal=True)

    def check_fx_valid(self, item2: "CKLine", method, for_virtual=False):
        """
        检查两个分型是否能构成一笔（顶分型与底分型之间的有效性验证）

        参数:
            item2: 另一个分型所在的合并K线（类型与 self 相反：self是顶则item2是底）
            method: 验证方法（FX_CHECK_METHOD 枚举）
            for_virtual: 是否用于虚段（虚笔）

        返回:
            True 如果两个分型之间满足笔的条件

        缠论知识 - 笔的构成条件：
        1. 顶分型和底分型之间至少有一根独立K线（不属于两个分型的K线）
        2. 顶分型的高点必须高于底分型的高点
        3. 底分型的低点必须低于顶分型的低点
        4. 不同的验证方法（HALF/LOSS/STRICT/TOTALLY）对应不同的严格程度

        四种验证方法对比：
        - STRICT（严格）：验证顶底分型及其前后K线，确保不重叠
        - LOSS（宽松）：只验证顶底分型本身
        - HALF（半严格）：验证前两根K线（顶分型+前一根，底分型+前一根）
        - TOTALLY（完全严格）：要求顶分型最低点 > 底分型最高点（完全无重叠）
        """
        assert self.next is not None and item2.pre is not None
        assert self.pre is not None
        assert item2.idx > self.idx

        if self.fx == FX_TYPE.TOP:
            # 当前是顶分型，检查与底分型的关系
            assert for_virtual or item2.fx == FX_TYPE.BOTTOM
            if for_virtual and item2.dir != KLINE_DIR.DOWN:
                return False

            # 根据不同的验证方法，选取不同的比较范围
            if method == FX_CHECK_METHOD.HALF:  # 检测前两KLC
                # 半严格：取顶分型+前一根的最低点，底分型+前一根的最高点
                item2_high = max([item2.pre.high, item2.high])
                self_low = min([self.low, self.next.low])
            elif method == FX_CHECK_METHOD.LOSS:  # 只检测顶底分形KLC
                # 宽松：只检查顶分型和底分型本身
                item2_high = item2.high
                self_low = self.low
            elif method in (FX_CHECK_METHOD.STRICT, FX_CHECK_METHOD.TOTALLY):
                # 严格/完全严格：取顶底分型及其前后K线
                if for_virtual:
                    item2_high = max([item2.pre.high, item2.high])
                else:
                    assert item2.next is not None
                    item2_high = max([item2.pre.high, item2.high, item2.next.high])
                self_low = min([self.pre.low, self.low, self.next.low])
            else:
                raise CChanException("bi_fx_check config error!", ErrCode.CONFIG_ERROR)

            if method == FX_CHECK_METHOD.TOTALLY:
                # 完全严格：顶分型最低点必须 > 底分型最高点（完全无重叠区间）
                return self.low > item2_high
            else:
                # 严格/半严格/宽松：顶分型高点 > 底分型高点，且顶分型低点 > 底分型低点
                return self.high > item2_high and item2.low < self_low

        elif self.fx == FX_TYPE.BOTTOM:
            # 当前是底分型，检查与顶分型的关系
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