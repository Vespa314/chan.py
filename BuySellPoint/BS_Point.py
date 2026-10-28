# -*- coding: utf-8 -*-
"""
买卖点模块 - 表示缠论中的买卖点

Java 开发者注意：
- Generic[LINE_TYPE] 是 Python 泛型，类似于 Java 的 <LINE_TYPE>
- Union[str, Dict, CFeatures] 类似于 Java 中的方法重载（不同参数类型）
- Optional[T] 类似于 Java 的 @Nullable T
"""

from typing import Dict, Generic, List, Optional, TypeVar, Union

from Bi.Bi import CBi
from ChanModel.Features import CFeatures
from Common.CEnum import BSP_TYPE
from Seg.Seg import CSeg

LINE_TYPE = TypeVar('LINE_TYPE', CBi, CSeg)


class CBS_Point(Generic[LINE_TYPE]):
    """
    买卖点 - 缠论中的交易信号

    缠论知识 - 买卖点分类：
    1. 第一类买卖点（T1）：中枢背驰后形成，是最重要的买卖点
    2. 第二类买卖点（T2）：回测中枢不破，确认第一类买卖点
    3. 第三类买卖点（T3A/T3B）：突破中枢后回测不破中枢，确认趋势延续
    4. 盘整背驰买卖点（T1P）：无中枢情况下的背驰买卖点
    5. 类二买卖点（T2S）：中枢内多次回测形成的买卖点

    属性说明：
    - bi: 买卖点所在的笔（或线段）
    - klu: 买卖点所在的K线
    - is_buy: True=买入点，False=卖出点
    - type: 买卖点类型列表（一个点可能同时是多种类型）
    - relate_bsp1: 关联的第一类买卖点
    - features: 买卖点的特征数据
    - is_segbsp: 是否是线段级别的买卖点
    """

    def __init__(self, bi: LINE_TYPE, is_buy, bs_type: BSP_TYPE, relate_bsp1: Optional['CBS_Point'], feature_dict=None):
        """
        初始化买卖点

        参数:
            bi: 买卖点所在的笔（或线段）
            is_buy: True=买入，False=卖出
            bs_type: 买卖点类型
            relate_bsp1: 关联的第一类买卖点（用于二/三类买卖点）
            feature_dict: 特征数据字典
        """
        self.bi: LINE_TYPE = bi
        self.klu = bi.get_end_klu()
        self.is_buy = is_buy
        self.type: List[BSP_TYPE] = [bs_type]
        self.relate_bsp1 = relate_bsp1

        self.bi.bsp = self  # 设置反向引用
        self.features = CFeatures(feature_dict)

        self.is_segbsp = False

        self.init_common_feature()

    def add_type(self, bs_type: BSP_TYPE):
        """
        添加买卖点类型（一个点可以同时是多种类型）

        例如：一个点可以同时是 T1 和 T1P
        """
        self.type.append(bs_type)

    def type2str(self):
        """买卖点类型转换为字符串，格式如 '1,2,3a'"""
        return ",".join([x.value for x in self.type])

    def add_another_bsp_prop(self, bs_type: BSP_TYPE, relate_bsp1):
        """
        添加另一个买卖点属性（同一位置被识别为多种类型）

        参数:
            bs_type: 新类型
            relate_bsp1: 关联的第一类买卖点
        """
        self.add_type(bs_type)
        if self.relate_bsp1 is None:
            self.relate_bsp1 = relate_bsp1
        elif relate_bsp1 is not None:
            assert self.relate_bsp1.klu.idx == relate_bsp1.klu.idx

    def add_feat(self, inp1: Union[str, Dict[str, float], Dict[str, Optional[float]], 'CFeatures'], inp2: Optional[float] = None):
        """
        添加特征数据

        参数:
            inp1: 特征名（str）/ 特征字典 / CFeatures 对象
            inp2: 特征值（当 inp1 是 str 时）
        """
        self.features.add_feat(inp1, inp2)

    def init_common_feature(self):
        """
        初始化通用特征

        添加所有买卖点都有的特征：笔的振幅
        """
        self.add_feat({
            'bsp_bi_amp': self.bi.amp(),
        })