class BIAS_Item:
    def __init__(self, bias1, bias2, bias3):
        self.bias1 = bias1
        self.bias2 = bias2
        self.bias3 = bias3


class BIAS:
    def __init__(self, fastperiod=6, midperiod=12, slowperiod=24):
        self.fastperiod = fastperiod
        self.midperiod = midperiod
        self.slowperiod = slowperiod
        self.arr1 = []
        self.arr2 = []
        self.arr3 = []
        self.pre_bias = BIAS_Item(0, 0, 0)

    def add(self, value) -> BIAS_Item:
        self.arr1.append(value)
        self.arr2.append(value)
        self.arr3.append(value)
        if len(self.arr1) > self.fastperiod:
            self.arr1 = self.arr1[-self.fastperiod:]
        if len(self.arr2) > self.midperiod:
            self.arr2 = self.arr2[-self.midperiod:]
        if len(self.arr3) > self.slowperiod:
            self.arr3 = self.arr3[-self.slowperiod:]
        ma1 = sum(self.arr1) / self.fastperiod
        ma2 = sum(self.arr2) / self.midperiod
        ma3 = sum(self.arr3) / self.slowperiod
        bias1 = (value - ma1) / ma1*100
        bias2 = (value - ma2) / ma2*100
        bias3 = (value - ma3) / ma3*100
        cur_bias = BIAS_Item(bias1, bias2, bias3)
        self.pre_bias = cur_bias
        return cur_bias
