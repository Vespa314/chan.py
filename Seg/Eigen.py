# -*- coding: utf-8 -*-
"""
特征序列元素模块 - 特征序列中合并后的"笔分组"

Java 开发者注意：
- CEigen 继承 CKLine_Combiner[CBi]，是泛型的具体化
  Java 对比：class CEigen extends CKLine_Combiner<CBi>
- super(CEigen, self).update_fx(...) 调用父类方法
  Java 对比：super.update_fx(...)
- Self 是 Python 3.11+ 的类型注解，表示当前类自身
"""

from typing import Self

from Bi.Bi import CBi
from Combiner.KLine_Combiner import CKLine_Combiner
from Common.CEnum import BI_DIR, FX_TYPE


class CEigen(CKLine_Combiner[CBi]):
    """
    特征序列元素 - 将笔视为"K线"进行合并

    缠论知识 - 特征序列：
    特征序列是缠论线段划分的核心概念。
    从某个方向看，线段由笔构成，把这些笔的"反方向笔"视为特征序列元素。
    例如：
    - 上升线段中，所有下降笔构成特征序列
    - 下降线段中，所有上升笔构成特征序列

    特征序列的合并规则与K线包含处理完全相同：
    - 先判断方向
    - 上升趋势：高高（取高点max，低点max）
    - 下降趋势：低低（取高点min，低点min）

    特殊属性 - gap：
    特征序列分型中，如果第一元素和第二元素之间存在跳空缺口，
    需要特殊处理（线段破坏的第二种情况）。
    """

    def __init__(self, bi, _dir):
        """
        初始化特征序列元素
        参数:
            bi: 第一笔
            _dir: 合并方向（KLINE_DIR.UP 或 KLINE_DIR.DOWN）
        """
        super(CEigen, self).__init__(bi, _dir)
        self.gap = False  # 是否存在跳空缺口

    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        """
        检测特征序列分形，同时判断是否存在跳空缺口

        跳空判断：
        - 顶分型：pre.high < self.low → 有跳空（前一元素高点 < 当前元素低点）
        - 底分型：pre.low > self.high → 有跳空（前一元素低点 > 当前元素高点）

        缠论知识 - 特征序列缺口：
        如果特征序列分型的第一元素和第二元素之间存在跳空，
        说明线段破坏可能是第二种情况，需要等待反向特征序列确认。
        """
        super(CEigen, self).update_fx(_pre, _next, exclude_included, allow_top_equal)
        if (self.fx == FX_TYPE.TOP and _pre.high < self.low) or \
           (self.fx == FX_TYPE.BOTTOM and _pre.low > self.high):
            self.gap = True

    def __str__(self):
        return f"{self.lst[0].idx}~{self.lst[-1].idx} gap={self.gap} fx={self.fx}"

    def GetPeakBiIdx(self):
        """
        获取特征序列分型对应的极值笔索引

        返回:
            分型形成时对应笔的索引

        缠论知识 - 分型对应笔：
        - 下降线段（上升特征序列）：顶分型对应高点所在的笔
        - 上升线段（下降特征序列）：底分型对应低点所在的笔

        注意：返回的是 idx-1，因为分型确认后线段的结束点是
        分型对应笔的前一笔（分型之前的笔才是线段的结束笔）。
        """
        assert self.fx != FX_TYPE.UNKNOWN
        bi_dir = self.lst[0].dir
        if bi_dir == BI_DIR.UP:  # 下降线段（特征序列是上升笔）
            return self.get_peak_klu(is_high=False).idx-1
        else:
            return self.get_peak_klu(is_high=True).idx-1