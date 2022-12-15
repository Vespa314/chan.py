from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode


class CTrendModel:
    def __init__(self, trend_type: TREND_TYPE, T: int):
        self.T = T
        self.arr = []
        self.type = trend_type

    def add(self, value) -> float:
        self.arr.append(value)
        if len(self.arr) > self.T:
            self.arr = self.arr[-self.T:]
        if self.type == TREND_TYPE.MEAN:
            return sum(self.arr)/len(self.arr)
        elif self.type == TREND_TYPE.MAX:
            return max(self.arr)
        elif self.type == TREND_TYPE.MIN:
            return min(self.arr)
        else:
            raise CChanException(f"Unknown trendModel Type = {self.type}", ErrCode.PARA_ERROR)
