# -*- coding: utf-8 -*-
"""
买卖点配置模块 - 买卖点计算的各项参数配置

Java 开发者注意：
- **args 是 Python 的关键字参数收集，类似于 Java 的 Map<String, Object>
  Java 对比：没有直接对应，通常用 Builder 模式实现
- exec() 是 Python 的动态执行函数，类似于 Java 的 ScriptEngine.eval()
  Java 对比：Java 没有直接对应的内置函数，需要用脚本引擎
- _parse_inf 用于处理无穷大值（float('inf')），使 eval() 能正确处理
"""

from typing import Dict, List, Optional

from Common.CEnum import BSP_TYPE, MACD_ALGO
from Common.func_util import _parse_inf


class CBSPointConfig:
    """
    买卖点配置 - 包含买入和卖出两套配置

    属性说明：
    - b_conf: 买入配置
    - s_conf: 卖出配置

    买卖点类型：
    - T1: 第一类买卖点（中枢背驰）
    - T1P: 盘整背驰买卖点（无中枢的背驰）
    - T2: 第二类买卖点（回测中枢）
    - T2S: 类二买卖点（中枢内的二次回测）
    - T3A: 第三类买卖点（中枢之后）
    - T3B: 第三类买卖点（中枢之前）
    """

    def __init__(self, **args):
        """
        初始化买卖点配置

        Python 语法：**args 收集所有关键字参数
        Java 对比：类似于可变参数 Map<String, Object>
        """
        self.b_conf = CPointConfig(**args)
        self.s_conf = CPointConfig(**args)

    def GetBSConfig(self, is_buy):
        """
        获取买卖点配置

        参数:
            is_buy: True=买入配置，False=卖出配置

        返回:
            CPointConfig 配置对象
        """
        return self.b_conf if is_buy else self.s_conf


class CPointConfig:
    """
    买卖点参数配置

    属性说明：
    - divergence_rate: 背驰率阈值（<1 表示离开笔力度小于进入笔）
    - min_zs_cnt: 最小中枢数量（用于第一类买卖点）
    - bsp1_only_multibi_zs: 是否只考虑多笔中枢
    - max_bs2_rate: 第二类买卖点的最大回撤率
    - macd_algo: 背驰判断的 MACD 算法
    - bs1_peak: 第一类买卖点是否要求极值
    - target_types: 目标买卖点类型列表
    - bsp2_follow_1: 第二类买卖点是否必须跟随第一类
    - bsp3_follow_1: 第三类买卖点是否必须跟随第一类
    - bsp3_peak: 第三类买卖点是否要求极值
    - bsp2s_follow_2: 类二买卖点是否必须跟随第二类
    - max_bsp2s_lv: 类二买卖点的最大层级
    - strict_bsp3: 严格第三类买卖点模式
    - bsp3a_max_zs_cnt: 第三类A买卖点的最大中枢数
    """

    def __init__(self,
                 divergence_rate,
                 min_zs_cnt,
                 bsp1_only_multibi_zs,
                 max_bs2_rate,
                 macd_algo,
                 bs1_peak,
                 bs_type,
                 bsp2_follow_1,
                 bsp3_follow_1,
                 bsp3_peak,
                 bsp2s_follow_2,
                 max_bsp2s_lv,
                 strict_bsp3,
                 bsp3a_max_zs_cnt,
                 ):
        self.divergence_rate = divergence_rate
        self.min_zs_cnt = min_zs_cnt
        self.bsp1_only_multibi_zs = bsp1_only_multibi_zs
        self.max_bs2_rate = max_bs2_rate
        assert self.max_bs2_rate <= 1
        self.SetMacdAlgo(macd_algo)
        self.bs1_peak = bs1_peak
        self.tmp_target_types = bs_type
        self.target_types: List[BSP_TYPE] = []
        self.bsp2_follow_1 = bsp2_follow_1
        self.bsp3_follow_1 = bsp3_follow_1
        self.bsp3_peak = bsp3_peak
        self.bsp2s_follow_2 = bsp2s_follow_2
        self.max_bsp2s_lv: Optional[int] = max_bsp2s_lv
        self.strict_bsp3 = strict_bsp3
        self.bsp3a_max_zs_cnt = bsp3a_max_zs_cnt
        assert self.bsp3a_max_zs_cnt >= 1

    def parse_target_type(self):
        """
        解析目标买卖点类型

        将字符串配置（如 "1,2,3a"）转换为 BSP_TYPE 枚举列表。
        仅在运行时调用一次。

        Python 语法：字典推导式 {x.value: x for x in BSP_TYPE}
        Java 对比：stream.collect(Collectors.toMap(BSP_TYPE::getValue, Function.identity()))
        """
        _d: Dict[str, BSP_TYPE] = {x.value: x for x in BSP_TYPE}
        if isinstance(self.tmp_target_types, str):
            self.tmp_target_types = [t.strip() for t in self.tmp_target_types.split(",")]
        for target_t in self.tmp_target_types:
            assert target_t in ['1', '2', '3a', '2s', '1p', '3b']
        self.target_types = [_d[_type] for _type in self.tmp_target_types]

    def SetMacdAlgo(self, macd_algo):
        """设置 MACD 算法（字符串 → 枚举）"""
        _d = {
            "area": MACD_ALGO.AREA,
            "peak": MACD_ALGO.PEAK,
            "full_area": MACD_ALGO.FULL_AREA,
            "diff": MACD_ALGO.DIFF,
            "slope": MACD_ALGO.SLOPE,
            "amp": MACD_ALGO.AMP,
            "amount": MACD_ALGO.AMOUNT,
            "volumn": MACD_ALGO.VOLUMN,
            "amount_avg": MACD_ALGO.AMOUNT_AVG,
            "volumn_avg": MACD_ALGO.VOLUMN_AVG,
            "turnrate_avg": MACD_ALGO.TURNRATE_AVG,
            "rsi": MACD_ALGO.RSI,
        }
        self.macd_algo = _d[macd_algo]

    def set(self, k, v):
        """
        动态设置属性（用于运行时配置）

        Python 语法：exec(f"self.{k} = {v}") 是动态执行代码
        Java 对比：Java 没有直接对应，需要用反射 Field.set()
        """
        v = _parse_inf(v)
        if k == "macd_algo":
            self.SetMacdAlgo(v)
        else:
            exec(f"self.{k} = {v}")