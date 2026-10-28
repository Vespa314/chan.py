# -*- coding: utf-8 -*-
"""
趋势模型模块 - 计算均线趋势指标（MA/MAX/MIN）

Java 开发者注意：
- Python 的 sum(arr)/len(arr) 类似于 Java 的 stream.average().orElse(0)
- Python 列表切片 arr[-T:] 取最后 T 个元素，类似于 Java 的 subList
- Python 可以重写类属性，类似于 Java 的 static 字段赋值
"""

from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode


class CTrendModel:
    """
    趋势模型计算器 - 计算指定周期的移动平均/最大值/最小值

    参数:
        trend_type: 趋势类型
          - MEAN: 移动平均线（MA）
          - MAX: 周期内最大值
          - MIN: 周期内最小值
        T: 周期长度

    缠论知识 - 均线在缠论中的应用：
    均线用于辅助判断趋势方向和多空分界。
    缠论中通常使用 5/10/20/60/120/250 等周期的均线。
    """

    def __init__(self, trend_type: TREND_TYPE, T: int):
        self.T = T
        self.arr = []
        self.type = trend_type

    def add(self, value) -> float:
        """
        添加新价格并计算趋势值

        参数:
            value: 新价格

        返回:
            计算后的趋势值

        根据 trend_type 不同：
        - MEAN: sum(arr) / len(arr) - 移动平均
        - MAX: max(arr) - 周期内最大值
        - MIN: min(arr) - 周期内最小值
        """
        self.arr.append(value)
        if len(self.arr) > self.T:
            self.arr = self.arr[-self.T:]  # 只保留最近 T 个值
        if self.type == TREND_TYPE.MEAN:
            return sum(self.arr)/len(self.arr)
        elif self.type == TREND_TYPE.MAX:
            return max(self.arr)
        elif self.type == TREND_TYPE.MIN:
            return min(self.arr)
        else:
            raise CChanException(f"Unknown trendModel Type = {self.type}", ErrCode.PARA_ERROR)