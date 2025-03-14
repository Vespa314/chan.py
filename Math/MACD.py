from typing import List

# 定义 CMACD_item 类，表示 MACD 指标的一个数据项
class CMACD_item:
    def __init__(self, fast_ema, slow_ema, DIF, DEA):
        self.fast_ema = fast_ema  # 快速指数移动平均
        self.slow_ema = slow_ema  # 慢速指数移动平均
        self.DIF = DIF  # DIF 值
        self.DEA = DEA  # DEA 值
        self.macd = 2 * (DIF - DEA)  # 计算 MACD 值

# 定义 CMACD 类，表示 MACD 指标的计算
class CMACD:
    def __init__(self, fastperiod=12, slowperiod=26, signalperiod=9):
        self.macd_info: List[CMACD_item] = []  # 存储 MACD 数据项的列表
        self.fastperiod = fastperiod  # 快速 EMA 的周期
        self.slowperiod = slowperiod  # 慢速 EMA 的周期
        self.signalperiod = signalperiod  # 信号线的周期

    # 添加新的价格值并计算相应的 MACD 数据项
    def add(self, value) -> CMACD_item:
        if not self.macd_info:  # 如果列表为空，初始化第一个数据项
            self.macd_info.append(CMACD_item(fast_ema=value, slow_ema=value, DIF=0, DEA=0))
        else:
            # 计算快速 EMA
            _fast_ema = (2 * value + (self.fastperiod - 1) * self.macd_info[-1].fast_ema) / (self.fastperiod + 1)
            # 计算慢速 EMA
            _slow_ema = (2 * value + (self.slowperiod - 1) * self.macd_info[-1].slow_ema) / (self.slowperiod + 1)
            # 计算 DIF
            _dif = _fast_ema - _slow_ema
            # 计算 DEA
            _dea = (2 * _dif + (self.signalperiod - 1) * self.macd_info[-1].DEA) / (self.signalperiod + 1)
            # 添加新的 MACD 数据项到列表中
            self.macd_info.append(CMACD_item(fast_ema=_fast_ema, slow_ema=_slow_ema, DIF=_dif, DEA=_dea))
        return self.macd_info[-1]  # 返回最新的 MACD 数据项