# -*- coding: utf-8 -*-
"""
MACD 指标模块 - 计算 MACD 指标（指数平滑异同移动平均线）

Java 开发者注意：
- Python 的 List[T] 类型注解类似于 Java 的 List<T>
- Python 类属性在 __init__ 中动态定义，不需要先声明
- Python 的 f-string 类似于 Java 的 String.format() 但更简洁
"""

from typing import List


class CMACD_item:
    """
    MACD 单项 - 存储某一时刻的 MACD 计算结果

    属性说明：
    - fast_ema: 快线 EMA（12日指数移动平均）
    - slow_ema: 慢线 EMA（26日指数移动平均）
    - DIF: 快慢线差值（DIF = fast_ema - slow_ema）
    - DEA: DIF 的 EMA（9日）
    - macd: MACD 柱 = 2 * (DIF - DEA)

    缠论知识 - MACD 背驰：
    当价格创新高/低但 MACD 柱面积或峰值没有同步创新高/低时，
    称为背驰，是重要的买卖信号。
    """

    def __init__(self, fast_ema, slow_ema, DIF, DEA):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.DIF = DIF
        self.DEA = DEA
        self.macd = 2 * (DIF - DEA)


class CMACD:
    """
    MACD 指标计算器

    标准 MACD 参数：fast=12, slow=26, signal=9

    EMA 计算公式：
    EMA_today = (2 * price + (N - 1) * EMA_yesterday) / (N + 1)
    这是 EMA 的递归计算公式，用于替代简单的 SMA。

    缠论知识 - MACD 在缠论中的应用：
    1. 背驰判断：比较相邻同向笔的 MACD 指标
    2. 面积法：笔区间内 MACD 柱的绝对值和
    3. 峰值法：笔区间内 MACD 柱的最大绝对值
    """

    def __init__(self, fastperiod=12, slowperiod=26, signalperiod=9):
        self.macd_info: List[CMACD_item] = []
        self.fastperiod = fastperiod
        self.slowperiod = slowperiod
        self.signalperiod = signalperiod

    def add(self, value) -> CMACD_item:
        """
        添加新价格并计算 MACD

        参数:
            value: 新价格（通常是收盘价）

        返回:
            最新计算的 CMACD_item

        计算流程：
        1. 第一个值：初始化 EMA 为价格本身，DIF=DEA=0
        2. 后续值：
           - 计算快线 EMA（fastperiod=12）
           - 计算慢线 EMA（slowperiod=26）
           - DIF = 快线EMA - 慢线EMA
           - DEA = DIF 的 EMA（signalperiod=9）
           - MACD柱 = 2 * (DIF - DEA)
        """
        if not self.macd_info:
            self.macd_info.append(CMACD_item(fast_ema=value, slow_ema=value, DIF=0, DEA=0))
        else:
            _fast_ema = (2 * value + (self.fastperiod - 1) * self.macd_info[-1].fast_ema) / (self.fastperiod + 1)
            _slow_ema = (2 * value + (self.slowperiod - 1) * self.macd_info[-1].slow_ema) / (self.slowperiod + 1)
            _dif = _fast_ema - _slow_ema
            _dea = (2 * _dif + (self.signalperiod - 1) * self.macd_info[-1].DEA) / (self.signalperiod + 1)
            self.macd_info.append(CMACD_item(fast_ema=_fast_ema, slow_ema=_slow_ema, DIF=_dif, DEA=_dea))
        return self.macd_info[-1]