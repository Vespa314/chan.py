# -*- coding: utf-8 -*-
"""
KDJ 指标模块 - 计算随机指标（Stochastic Oscillator）

Java 开发者注意：
- Python 字典 {'key': value} 类似于 Java 的 Map.of("key", value) 或 HashMap
- Python 列表的 pop(0) 删除第一个元素，类似于 Java 的 LinkedList.removeFirst()
- Python 的 max/min 可以接受列表推导式，类似于 Java 的 Stream.max/min
"""


class KDJ_Item:
    """KDJ 单项 - 存储 K/D/J 三个值"""

    def __init__(self, k, d, j):
        self.k = k
        self.d = d
        self.j = j


class KDJ:
    """
    KDJ（随机指标）计算器

    参数:
        period: KDJ 周期（默认 9）

    计算流程：
    1. RSV = 100 * (收盘价 - 最低价) / (最高价 - 最低价)
    2. K = 2/3 * 前日K + 1/3 * RSV
    3. D = 2/3 * 前日D + 1/3 * K
    4. J = 3*K - 2*D

    缠论知识 - KDJ 在缠论中的应用：
    KDJ 用于辅助判断超买超卖和背驰，
    通常与 MACD 配合使用，增加背驰判断的可靠性。
    """

    def __init__(self, period: int = 9):
        super(KDJ, self).__init__()
        self.arr = []
        self.period = period
        self.pre_kdj = KDJ_Item(50, 50, 50)  # 初始值：中性

    def add(self, high, low, close) -> KDJ_Item:
        """
        添加新价格并计算 KDJ

        参数:
            high: 最高价
            low: 最低价
            close: 收盘价

        返回:
            KDJ_Item 对象
        """
        self.arr.append({
            'high': high,
            'low': low,
        })
        if len(self.arr) > self.period:
            self.arr.pop(0)  # 保持窗口大小，删除最旧的数据

        # RSV 计算
        hn = max([x['high'] for x in self.arr])  # 周期内最高价
        ln = min([x['low'] for x in self.arr])   # 周期内最低价
        cn = close
        rsv = 100 * (cn - ln) / (hn - ln) if hn != ln else 0.0

        # K/D/J 平滑计算
        cur_k = 2 / 3 * self.pre_kdj.k + 1 / 3 * rsv
        cur_d = 2 / 3 * self.pre_kdj.d + 1 / 3 * cur_k
        cur_j = 3 * cur_k - 2 * cur_d
        cur_kdj = KDJ_Item(cur_k, cur_d, cur_j)
        self.pre_kdj = cur_kdj

        return cur_kdj