from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode

# 定义趋势模型类
class CTrendModel:
    def __init__(self, trend_type: TREND_TYPE, T: int):
        self.T = T  # 设置窗口大小 T
        self.arr = []  # 初始化存储值的列表
        self.type = trend_type  # 设置趋势类型

    # 添加新值并计算相应的趋势值
    def add(self, value) -> float:
        self.arr.append(value)  # 将新值添加到列表中
        # 如果列表长度超过窗口大小 T，则只保留最近 T 个值
        if len(self.arr) > self.T:
            self.arr = self.arr[-self.T:]

        # 根据趋势类型计算并返回相应的值
        if self.type == TREND_TYPE.MEAN:  # 如果趋势类型是均值
            return sum(self.arr) / len(self.arr)  # 返回均值
        elif self.type == TREND_TYPE.MAX:  # 如果趋势类型是最大值
            return max(self.arr)  # 返回最大值
        elif self.type == TREND_TYPE.MIN:  # 如果趋势类型是最小值
            return min(self.arr)  # 返回最小值
        else:
            # 如果趋势类型未知，抛出异常
            raise CChanException(f"Unknown trendModel Type = {self.type}", ErrCode.PARA_ERROR)