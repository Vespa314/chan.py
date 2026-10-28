# -*- coding: utf-8 -*-
"""
布林带指标模块 - 计算 BOLL（布林带）指标

Java 开发者注意：
- Python 的 math.sqrt 类似于 Java 的 Math.sqrt()
- Python 的 sum() 是内置函数，类似于 Java 的 stream.mapToDouble().sum()
- Python 的列表切片 arr[-N:] 取最后 N 个元素，类似于 Java 的 subList
"""

import math


def _truncate(x):
    """
    截断零值为极小值，防止除零错误

    Python 特性：三元表达式 x if cond else y
    Java 对比：cond ? x : y
    """
    return x if x != 0 else 1e-7


class BOLL_Metric:
    """
    布林带单项 - 存储某一时刻的布林带计算结果

    属性说明：
    - theta: 标准差
    - UP: 上轨 = MA + 2*标准差
    - DOWN: 下轨 = MA - 2*标准差
    - MID: 中轨 = MA（移动平均线）

    缠论知识 - 布林带在缠论中的应用：
    布林带用于判断价格波动范围和趋势强度。
    布林带收窄表示可能变盘，开口表示趋势延续。
    """

    def __init__(self, ma, theta):
        self.theta = _truncate(theta)
        self.UP = ma + 2*theta
        self.DOWN = _truncate(ma - 2*theta)
        self.MID = ma


class BollModel:
    """
    布林带计算器

    参数:
        N: 移动平均周期（默认 20）

    计算流程：
    1. 维护最近 N 个价格
    2. MA = sum(price) / N
    3. 标准差 = sqrt(sum((price - MA)^2) / N)
    4. 上轨 = MA + 2*标准差
    5. 下轨 = MA - 2*标准差
    """

    def __init__(self, N=20):
        assert N > 1
        self.N = N
        self.arr = []

    def add(self, value) -> BOLL_Metric:
        """
        添加新价格并计算布林带

        参数:
            value: 新价格

        返回:
            BOLL_Metric 对象

        Python 语法：生成器表达式 (x-ma)**2 for x in self.arr
        Java 对比：stream.map(x -> (x-ma)*(x-ma)).sum()
        """
        self.arr.append(value)
        if len(self.arr) > self.N:
            self.arr = self.arr[-self.N:]  # 只保留最近 N 个值
        ma = sum(self.arr)/len(self.arr)
        theta = math.sqrt(sum((x-ma)**2 for x in self.arr) / len(self.arr))
        return BOLL_Metric(ma, theta)