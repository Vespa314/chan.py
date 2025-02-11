class KDJ_Item:
    def __init__(self, k, d, j):
        self.k = k  # K值
        self.d = d  # D值
        self.j = j  # J值

class KDJ:
    def __init__(self, period: int = 9):
        super(KDJ, self).__init__()
        self.arr = []  # 存储高低价的列表
        self.period = period  # KDJ计算的周期，默认为9
        self.pre_kdj = KDJ_Item(50, 50, 50)  # 初始化前一个KDJ值，默认值为50

    # 添加新的高、低、收盘价，并计算当前的KDJ值
    def add(self, high, low, close) -> KDJ_Item:
        self.arr.append({
            'high': high,  # 添加当前的最高价
            'low': low,    # 添加当前的最低价
        })
        # 如果存储的价格数据超过周期，则移除最早的数据
        if len(self.arr) > self.period:
            self.arr.pop(0)

        # 计算当前周期内的最高价和最低价
        hn = max([x['high'] for x in self.arr])  # 当前周期内的最高价
        ln = min([x['low'] for x in self.arr])    # 当前周期内的最低价
        cn = close  # 当前的收盘价

        # 计算RSV值
        rsv = 100 * (cn - ln) / (hn - ln) if hn != ln else 0.0

        # 计算当前的K、D、J值
        cur_k = 2 / 3 * self.pre_kdj.k + 1 / 3 * rsv  # 当前K值
        cur_d = 2 / 3 * self.pre_kdj.d + 1 / 3 * cur_k  # 当前D值
        cur_j = 3 * cur_k - 2 * cur_d  # 当前J值

        # 创建当前的KDJ项
        cur_kdj = KDJ_Item(cur_k, cur_d, cur_j)
        self.pre_kdj = cur_kdj  # 更新前一个KDJ值

        return cur_kdj  # 返回当前的KDJ值