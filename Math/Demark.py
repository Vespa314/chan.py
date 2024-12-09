import copy
from dataclasses import dataclass
from typing import List, Literal, Optional, TypedDict
from Common.CEnum import BI_DIR

# 定义 K线数据类
@dataclass
class C_KL:
    idx: int  # K线索引
    close: float  # 收盘价
    high: float  # 最高价
    low: float  # 最低价

    # 根据是否为收盘价和方向返回相应的值
    def v(self, is_close: bool, _dir: BI_DIR) -> float:
        if is_close:
            return self.close
        return self.high if _dir == BI_DIR.UP else self.low

# 定义布林带类型
T_DEMARK_TYPE = Literal['setup', 'countdown']

# 定义类型字典，用于存储布林带信息
class T_DEMARK_INDEX(TypedDict):
    type: T_DEMARK_TYPE  # 类型（setup 或 countdown）
    dir: BI_DIR  # 方向
    idx: int  # 索引
    series: 'CDemarkSetup'  # 关联的 CDemarkSetup 对象

# 定义 CDemarkIndex 类，用于管理布林带数据
class CDemarkIndex:
    def __init__(self):
        self.data: List[T_DEMARK_INDEX] = []  # 存储布林带数据的列表

    # 添加新的布林带数据
    def add(self, _dir: BI_DIR, _type: T_DEMARK_TYPE, idx: int, series: 'CDemarkSetup'):
        self.data.append({"dir": _dir, "idx": idx, "type": _type, "series": series})

    # 获取所有 setup 类型的数据
    def get_setup(self) -> List[T_DEMARK_INDEX]:
        return [info for info in self.data if info['type'] == 'setup']

    # 获取所有 countdown 类型的数据
    def get_countdown(self) -> List[T_DEMARK_INDEX]:
        return [info for info in self.data if info['type'] == 'countdown']

    # 更新数据
    def update(self, demark_index: 'CDemarkIndex'):
        self.data.extend(demark_index.data)

# 定义 CDemarkCountdown 类，用于处理 countdown 逻辑
class CDemarkCountdown:
    def __init__(self, _dir: BI_DIR, kl_list: List[C_KL], TDST_peak: float):
        self.dir = _dir  # 方向
        self.kl_list: List[C_KL] = copy.deepcopy(kl_list)  # K线列表的深拷贝
        self.idx = 0  # 当前计数器索引
        self.TDST_peak = TDST_peak  # TDST 峰值
        self.finish = False  # 是否完成标志

    # 更新 K线并返回是否成功
    def update(self, kl: C_KL) -> bool:
        if self.finish:
            return False
        self.kl_list.append(kl)  # 添加新的 K线
        if len(self.kl_list) <= CDemarkEngine.COUNTDOWN_BIAS:
            return False
        if self.idx == CDemarkEngine.MAX_COUNTDOWN:
            self.finish = True  # 达到最大计数，标记为完成
            return False
        # 检查是否超出 TDST 峰值
        if (self.dir == BI_DIR.DOWN and kl.high > self.TDST_peak) or (self.dir == BI_DIR.UP and kl.low < self.TDST_peak):
            self.finish = True
            return False
        # 检查是否满足计数条件
        if self.dir == BI_DIR.DOWN and self.kl_list[-1].close < self.kl_list[-1 - CDemarkEngine.COUNTDOWN_BIAS].v(CDemarkEngine.COUNTDOWN_CMP2CLOSE, self.dir):
            self.idx += 1
            return True
        if self.dir == BI_DIR.UP and self.kl_list[-1].close > self.kl_list[-1 - CDemarkEngine.COUNTDOWN_BIAS].v(CDemarkEngine.COUNTDOWN_CMP2CLOSE, self.dir):
            self.idx += 1
            return True
        return False

# 定义 CDemarkSetup 类，用于处理 setup 逻辑
class CDemarkSetup:
    def __init__(self, _dir: BI_DIR, kl_list: List[C_KL], pre_kl: C_KL):
        self.dir = _dir  # 方向
        self.kl_list: List[C_KL] = copy.deepcopy(kl_list)  # K线列表的深拷贝
        self.pre_kl = pre_kl  # 前一根 K线，用于跳空时的比较
        assert len(self.kl_list) == CDemarkEngine.SETUP_BIAS  # 确保 K线数量正确
        self.countdown: Optional[CDemarkCountdown] = None  # 初始化 countdown
        self.setup_finished = False  # setup 是否完成的标志
        self.idx = 0  # 当前索引
        self.TDST_peak: Optional[float] = None  # TDST 峰值
        self.last_demark_index = CDemarkIndex()  # 缓存用

    # 更新 K线并返回 CDemarkIndex
    def update(self, kl: C_KL) -> CDemarkIndex:
        self.last_demark_index = CDemarkIndex()  # 初始化缓存
        if not self.setup_finished:
            self.kl_list.append(kl)  # 添加新的 K线
            # 根据方向判断是否完成 setup
            if self.dir == BI_DIR.DOWN:
                if self.kl_list[-1].close < self.kl_list[-1 - CDemarkEngine.SETUP_BIAS].v(CDemarkEngine.SETUP_CMP2CLOSE, self.dir):
                    self.add_setup()  # 添加 setup
                else:
                    self.setup_finished = True  # 标记为完成
            elif self.kl_list[-1].close > self.kl_list[-1 - CDemarkEngine.SETUP_BIAS].v(CDemarkEngine.SETUP_CMP2CLOSE, self.dir):
                self.add_setup()  # 添加 setup
            else:
                self.setup_finished = True  # 标记为完成
        # 如果达到 DEMARK_LEN 且没有完成 setup，初始化 countdown
        if self.idx == CDemarkEngine.DEMARK_LEN and not self.setup_finished and self.countdown is None:
            self.countdown = CDemarkCountdown(self.dir, self.kl_list[:-1], self.cal_TDST_peak())
        # 更新 countdown
        if self.countdown is not None and self.countdown.update(kl):
            self.last_demark_index.add(self.dir, 'countdown', self.countdown.idx, self)
        return self.last_demark_index  # 返回缓存的数据

    # 添加 setup 数据
    def add_setup(self):
        self.idx += 1
        self.last_demark_index.add(self.dir, 'setup', self.idx, self)

    # 计算 TDST 峰值
    def cal_TDST_peak(self) -> float:
        assert len(self.kl_list) == CDemarkEngine.SETUP_BIAS + CDemarkEngine.DEMARK_LEN  # 确保 K线数量正确
        arr = self.kl_list[CDemarkEngine.SETUP_BIAS:CDemarkEngine.SETUP_BIAS + CDemarkEngine.DEMARK_LEN]  # 获取相关 K线
        assert len(arr) == CDemarkEngine.DEMARK_LEN  # 确保 K线数量正确
        # 根据方向计算峰值
        if self.dir == BI_DIR.DOWN:
            res = max(kl.high for kl in arr)  # 计算最高价
            if CDemarkEngine.TIAOKONG_ST and arr[0].high < self.pre_kl.close:
                res = max(res, self.pre_kl.close)  # 跳空时更新峰值
        else:
            res = min(kl.low for kl in arr)  # 计算最低价
            if CDemarkEngine.TIAOKONG_ST and arr[0].low > self.pre_kl.close:
                res = min(res, self.pre_kl.close)  # 跳空时更新峰值
        self.TDST_peak = res  # 设置 TDST 峰值
        return res  # 返回峰值

# 定义 CDemarkEngine 类，管理整个 Demark 指标的逻辑
class CDemarkEngine:
    DEMARK_LEN = 9  # Demark 长度
    SETUP_BIAS = 4  # setup 偏移
    COUNTDOWN_BIAS = 2  # countdown 偏移
    MAX_COUNTDOWN = 13  # 最大 countdown 次数
    TIAOKONG_ST = True  # 第一根跳空时是否跟前一根的 close 比较
    SETUP_CMP2CLOSE = True  # setup 比较收盘价
    COUNTDOWN_CMP2CLOSE = True  # countdown 比较收盘价

    def __init__(
        self,
        demark_len=9,
        setup_bias=4,
        countdown_bias=2,
        max_countdown=13,
        tiaokong_st=True,
        setup_cmp2close=True,
        countdown_cmp2close=True
    ):
        # 初始化参数
        CDemarkEngine.DEMARK_LEN = demark_len
        CDemarkEngine.SETUP_BIAS = setup_bias
        CDemarkEngine.COUNTDOWN_BIAS = countdown_bias
        CDemarkEngine.MAX_COUNTDOWN = max_countdown
        CDemarkEngine.TIAOKONG_ST = tiaokong_st
        CDemarkEngine.SETUP_CMP2CLOSE = setup_cmp2close
        CDemarkEngine.COUNTDOWN_CMP2CLOSE = countdown_cmp2close
        self.kl_lst: List[C_KL] = []  # K线列表
        self.series: List[CDemarkSetup] = []  # setup 列表

    # 更新 K线数据并返回 CDemarkIndex
    def update(self, idx: int, close: float, high: float, low: float) -> CDemarkIndex:
        self.kl_lst.append(C_KL(idx, close, high, low))  # 添加新的 K线
        if len(self.kl_lst) <= CDemarkEngine.SETUP_BIAS + 1:
            return CDemarkIndex()  # 如果 K线数量不足，返回空的 CDemarkIndex
        # 判断当前 K线是否满足 setup 条件
        if self.kl_lst[-1].close < self.kl_lst[-1 - self.SETUP_BIAS].close:
            # 如果没有正在进行的下跌 setup，则添加新的下跌 setup
            if not any(series.dir == BI_DIR.DOWN and not series.setup_finished for series in self.series):
                self.series.append(CDemarkSetup(BI_DIR.DOWN, self.kl_lst[-CDemarkEngine.SETUP_BIAS - 1:-1], self.kl_lst[-CDemarkEngine.SETUP_BIAS - 2]))
            # 标记已经完成的上升 series
            for series in self.series:
                if series.dir == BI_DIR.UP and series.countdown is None and not series.setup_finished:
                    series.setup_finished = True
        elif self.kl_lst[-1].close > self.kl_lst[-1 - self.SETUP_BIAS].close:
            # 如果没有正在进行的上升 setup，则添加新的上升 setup
            if not any(series.dir == BI_DIR.UP and not series.setup_finished for series in self.series):
                self.series.append(CDemarkSetup(BI_DIR.UP, self.kl_lst[-CDemarkEngine.SETUP_BIAS - 1:-1], self.kl_lst[-CDemarkEngine.SETUP_BIAS - 2]))
            # 标记已经完成的下跌 series
            for series in self.series:
                if series.dir == BI_DIR.DOWN and series.countdown is None and not series.setup_finished:
                    series.setup_finished = True
        self.clear()  # 清理无效的 series
        self.clean_series_from_setup_finish()  # 清理已完成的 setup
        result = self.cal_result()  # 计算结果
        self.clear()  # 再次清理
        return result  # 返回结果

    # 计算最终的 CDemarkIndex
    def cal_result(self) -> CDemarkIndex:
        demark_index = CDemarkIndex()  # 创建新的 CDemarkIndex
        for series in self.series:
            demark_index.update(series.last_demark_index)  # 更新 demark_index
        return demark_index  # 返回结果

    # 清理无效的 series
    def clear(self):
        # 清理已完成但没有 countdown 的 series
        invalid_series = [series for series in self.series if series.setup_finished and series.countdown is None]
        for s in invalid_series:
            self.series.remove(s)
        # 清理已完成 countdown 的 series
        invalid_series = [series for series in self.series if series.countdown is not None and series.countdown.finish]
        for s in invalid_series:
            self.series.remove(s)

    # 清理已完成的 setup
    def clean_series_from_setup_finish(self):
        finished_setup: Optional[int] = None  # 标记完成的 setup
        for series in self.series:
            demark_idx = series.update(self.kl_lst[-1])  # 更新 series
            for setup_idx in demark_idx.get_setup():
                if setup_idx['idx'] == CDemarkEngine.DEMARK_LEN:
                    assert finished_setup is None  # 确保只有一个完成的 setup
                    finished_setup = id(series)  # 记录完成的 setup
        if finished_setup is not None:
            self.series = [series for series in self.series if id(series) == finished_setup]  # 只保留完成的 setup