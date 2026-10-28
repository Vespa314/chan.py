# -*- coding: utf-8 -*-
"""
Demark 序列指标模块 - 计算 TD 序列（Setup 和 Countdown）

Java 开发者注意：
- @dataclass 是 Python 3.7+ 的数据类装饰器，自动生成 __init__/__eq__/__repr__
  Java 对比：类似于 Java 14+ 的 record 类型，或 Lombok 的 @Data 注解
- TypedDict 是 Python 的类型化字典，类似于 Java 中有固定字段的 Map
- Literal 是 Python 的字面量类型约束，类似于 Java 的 enum 但更灵活
  Java 对比：没有直接对应，通常用 enum 替代
- Python 的 id() 函数返回对象内存地址，类似于 Java 的 System.identityHashCode()
"""

import copy
from dataclasses import dataclass
from typing import List, Literal, Optional, TypedDict

from Common.CEnum import BI_DIR


@dataclass
class C_KL:
    """
    Demark 用 K 线数据类

    Python 特性：@dataclass 自动生成 __init__, __eq__, __repr__
    Java 对比：Java 14+ record 或 Lombok @Data
    """
    idx: int
    close: float
    high: float
    low: float

    def v(self, is_close: bool, _dir: BI_DIR) -> float:
        """
        获取比较用的价格

        参数:
            is_close: True=用收盘价，False=根据方向用最高/最低价
            _dir: 方向

        返回:
            close 或 high/low
        """
        if is_close:
            return self.close
        return self.high if _dir == BI_DIR.UP else self.low


T_DEMARK_TYPE = Literal['setup', 'countdown']


class T_DEMARK_INDEX(TypedDict):
    """
    Demark 索引的类型化字典

    Python 特性：TypedDict 定义字典的键和值类型
    Java 对比：类似于有固定字段的 POJO/DTO
    """
    type: T_DEMARK_TYPE
    dir: BI_DIR
    idx: int
    series: 'CDemarkSetup'


class CDemarkIndex:
    """
    Demark 索引存储 - 存储 K 线的 Demark 序列索引

    缠论知识 - Demark 序列：
    Demark 序列（TD 序列）是一种用于识别趋势衰竭的技术指标。
    由两部分组成：
    - Setup（结构）：连续 9 根 K 线满足条件
    - Countdown（倒计时）：Setup 完成后，最多 13 次倒计时

    用于辅助判断趋势反转的时机。
    """

    def __init__(self):
        self.data: List[T_DEMARK_INDEX] = []

    def add(self, _dir: BI_DIR, _type: T_DEMARK_TYPE, idx: int, series: 'CDemarkSetup'):
        """添加 Demark 索引"""
        self.data.append({"dir": _dir, "idx": idx, "type": _type, "series": series})

    def get_setup(self) -> List[T_DEMARK_INDEX]:
        """获取所有 Setup 索引"""
        return [info for info in self.data if info['type'] == 'setup']

    def get_countdown(self) -> List[T_DEMARK_INDEX]:
        """获取所有 Countdown 索引"""
        return [info for info in self.data if info['type'] == 'countdown']

    def update(self, demark_index: 'CDemarkIndex'):
        """合并另一个 DemarkIndex 的数据"""
        self.data.extend(demark_index.data)


class CDemarkCountdown:
    """
    Demark 倒计时计算器

    Countdown 阶段：
    在 Setup 完成后，最多 13 次倒计时。
    每次倒计时需要满足收盘价与之前 K 线的比较条件。

    终止条件：
    - 达到 MAX_COUNTDOWN（13次）
    - 价格突破 TDST 峰值（趋势衰竭确认）
    """

    def __init__(self, _dir: BI_DIR, kl_list: List[C_KL], TDST_peak: float):
        self.dir = _dir
        self.kl_list: List[C_KL] = copy.deepcopy(kl_list)
        self.idx = 0
        self.TDST_peak = TDST_peak  # Setup 阶段的极值
        self.finish = False

    def update(self, kl: C_KL) -> bool:
        """
        更新倒计时

        参数:
            kl: 新 K 线

        返回:
            True 如果倒计时+1
        """
        if self.finish:
            return False
        self.kl_list.append(kl)
        if len(self.kl_list) <= CDemarkEngine.COUNTDOWN_BIAS:
            return False
        if self.idx == CDemarkEngine.MAX_COUNTDOWN:
            self.finish = True
            return False
        # 突破 TDST 峰值 → 终止
        if (self.dir == BI_DIR.DOWN and kl.high > self.TDST_peak) or \
           (self.dir == BI_DIR.UP and kl.low < self.TDST_peak):
            self.finish = True
            return False
        # 收盘价比较（与之前的 K 线比较）
        if self.dir == BI_DIR.DOWN and self.kl_list[-1].close < self.kl_list[-1 - CDemarkEngine.COUNTDOWN_BIAS].v(CDemarkEngine.COUNTDOWN_CMP2CLOSE, self.dir):
            self.idx += 1
            return True
        if self.dir == BI_DIR.UP and self.kl_list[-1].close > self.kl_list[-1 - CDemarkEngine.COUNTDOWN_BIAS].v(CDemarkEngine.COUNTDOWN_CMP2CLOSE, self.dir):
            self.idx += 1
            return True
        return False


class CDemarkSetup:
    """
    Demark Setup 计算器

    Setup 阶段：
    连续 9 根 K 线满足收盘价比较条件。
    需要 4 根前置 K 线（SETUP_BIAS）作为比较基准。

    缠论知识 - TD Setup：
    - 下降 Setup：收盘价 < 4 根前的收盘价 → Setup+1
    - 上升 Setup：收盘价 > 4 根前的收盘价 → Setup+1
    - 连续 9 次满足 → Setup 完成
    """

    def __init__(self, _dir: BI_DIR, kl_list: List[C_KL], pre_kl: C_KL):
        self.dir = _dir
        self.kl_list: List[C_KL] = copy.deepcopy(kl_list)
        self.pre_kl = pre_kl  # 跳空时使用
        assert len(self.kl_list) == CDemarkEngine.SETUP_BIAS
        self.countdown: Optional[CDemarkCountdown] = None
        self.setup_finished = False
        self.idx = 0
        self.TDST_peak: Optional[float] = None

        self.last_demark_index = CDemarkIndex()  # 缓存最近一次结果

    def update(self, kl: C_KL) -> CDemarkIndex:
        """更新 Setup 和 Countdown"""
        self.last_demark_index = CDemarkIndex()
        if not self.setup_finished:
            self.kl_list.append(kl)
            if self.dir == BI_DIR.DOWN:
                if self.kl_list[-1].close < self.kl_list[-1-CDemarkEngine.SETUP_BIAS].v(CDemarkEngine.SETUP_CMP2CLOSE, self.dir):
                    self.add_setup()
                else:
                    self.setup_finished = True
            elif self.kl_list[-1].close > self.kl_list[-1-CDemarkEngine.SETUP_BIAS].v(CDemarkEngine.SETUP_CMP2CLOSE, self.dir):
                self.add_setup()
            else:
                self.setup_finished = True
        if self.idx == CDemarkEngine.DEMARK_LEN and not self.setup_finished and self.countdown is None:
            self.countdown = CDemarkCountdown(self.dir, self.kl_list[:-1], self.cal_TDST_peak())
        if self.countdown is not None and self.countdown.update(kl):
            self.last_demark_index.add(self.dir, 'countdown', self.countdown.idx, self)
        return self.last_demark_index

    def add_setup(self):
        """Setup 计数+1"""
        self.idx += 1
        self.last_demark_index.add(self.dir, 'setup', self.idx, self)

    def cal_TDST_peak(self) -> float:
        """
        计算 TDST 峰值

        TDST = Setup 区间（9根K线）的极值
        - 下降 Setup：取最高价
        - 上升 Setup：取最低价

        如果第一根K线跳空，还要与 pre_kl 的收盘价比较。
        """
        assert len(self.kl_list) == CDemarkEngine.SETUP_BIAS+CDemarkEngine.DEMARK_LEN
        arr = self.kl_list[CDemarkEngine.SETUP_BIAS:CDemarkEngine.SETUP_BIAS+CDemarkEngine.DEMARK_LEN]
        assert len(arr) == CDemarkEngine.DEMARK_LEN
        if self.dir == BI_DIR.DOWN:
            res = max(kl.high for kl in arr)
            if CDemarkEngine.TIAOKONG_ST and arr[0].high < self.pre_kl.close:
                res = max(res, self.pre_kl.close)
        else:
            res = min(kl.low for kl in arr)
            if CDemarkEngine.TIAOKONG_ST and arr[0].low > self.pre_kl.close:
                res = min(res, self.pre_kl.close)
        self.TDST_peak = res
        return res


class CDemarkEngine:
    """
    Demark 序列引擎

    参数配置：
    - DEMARK_LEN = 9: Setup 需要连续 9 根 K 线
    - SETUP_BIAS = 4: 比较偏移量（与 4 根前的 K 线比较）
    - COUNTDOWN_BIAS = 2: Countdown 比较偏移量
    - MAX_COUNTDOWN = 13: 最大倒计时次数
    - TIAOKONG_ST: 跳空时是否与前一跟K线的 close 比较
    - SETUP_CMP2CLOSE: Setup 比较用收盘价还是高/低价
    - COUNTDOWN_CMP2CLOSE: Countdown 比较用收盘价还是高/低价
    """

    DEMARK_LEN = 9
    SETUP_BIAS = 4
    COUNTDOWN_BIAS = 2
    MAX_COUNTDOWN = 13
    TIAOKONG_ST = True
    SETUP_CMP2CLOSE = True
    COUNTDOWN_CMP2CLOSE = True

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
        """
        初始化 Demark 引擎

        Python 特性：类属性直接赋值 CDemarkEngine.DEMARK_LEN = ... 修改类级别属性
        Java 对比：类似于 static 字段赋值，但 Python 中类属性是类对象上的属性
        """
        CDemarkEngine.DEMARK_LEN = demark_len
        CDemarkEngine.SETUP_BIAS = setup_bias
        CDemarkEngine.COUNTDOWN_BIAS = countdown_bias
        CDemarkEngine.MAX_COUNTDOWN = max_countdown
        CDemarkEngine.TIAOKONG_ST = tiaokong_st
        CDemarkEngine.SETUP_CMP2CLOSE = setup_cmp2close
        CDemarkEngine.COUNTDOWN_CMP2CLOSE = countdown_cmp2close

        self.kl_lst: List[C_KL] = []
        self.series: List[CDemarkSetup] = []

    def update(self, idx: int, close: float, high: float, low: float) -> CDemarkIndex:
        """
        更新 Demark 序列

        参数:
            idx: K 线索引
            close: 收盘价
            high: 最高价
            low: 最低价

        返回:
            CDemarkIndex 对象

        处理流程：
        1. 添加新 K 线
        2. 如果收盘价满足 Setup 条件，创建新的 Setup 序列
        3. 关闭相反方向的 Setup 序列
        4. 清理无效序列
        5. 更新所有序列并返回结果
        """
        self.kl_lst.append(C_KL(idx, close, high, low))
        if len(self.kl_lst) <= CDemarkEngine.SETUP_BIAS+1:
            return CDemarkIndex()

        # 检查是否需要创建新的 Setup
        if self.kl_lst[-1].close < self.kl_lst[-1-self.SETUP_BIAS].close:
            if not any(series.dir == BI_DIR.DOWN and not series.setup_finished for series in self.series):
                self.series.append(CDemarkSetup(BI_DIR.DOWN, self.kl_lst[-CDemarkEngine.SETUP_BIAS-1:-1], self.kl_lst[-CDemarkEngine.SETUP_BIAS-2]))
            for series in self.series:
                if series.dir == BI_DIR.UP and series.countdown is None and not series.setup_finished:
                    series.setup_finished = True
        elif self.kl_lst[-1].close > self.kl_lst[-1-self.SETUP_BIAS].close:
            if not any(series.dir == BI_DIR.UP and not series.setup_finished for series in self.series):
                self.series.append(CDemarkSetup(BI_DIR.UP, self.kl_lst[-CDemarkEngine.SETUP_BIAS-1:-1], self.kl_lst[-CDemarkEngine.SETUP_BIAS-2]))
            for series in self.series:
                if series.dir == BI_DIR.DOWN and series.countdown is None and not series.setup_finished:
                    series.setup_finished = True

        self.clear()
        self.clean_series_from_setup_finish()

        result = self.cal_result()
        self.clear()
        return result

    def cal_result(self) -> CDemarkIndex:
        """汇总所有序列的 Demark 索引"""
        demark_index = CDemarkIndex()
        for series in self.series:
            demark_index.update(series.last_demark_index)
        return demark_index

    def clear(self):
        """清理无效序列（Setup 完成但无 Countdown，或 Countdown 已完成）"""
        invalid_series = [series for series in self.series if series.setup_finished and series.countdown is None]
        for s in invalid_series:
            self.series.remove(s)
        invalid_series = [series for series in self.series if series.countdown is not None and series.countdown.finish]
        for s in invalid_series:
            self.series.remove(s)

    def clean_series_from_setup_finish(self):
        """
        当 Setup 完成时，清理其他序列只保留完成的序列

        Python 特性：id(series) 返回对象的内存地址
        Java 对比：System.identityHashCode(series)
        """
        finished_setup: Optional[int] = None
        for series in self.series:
            demark_idx = series.update(self.kl_lst[-1])
            for setup_idx in demark_idx.get_setup():
                if setup_idx['idx'] == CDemarkEngine.DEMARK_LEN:
                    assert finished_setup is None
                    finished_setup = id(series)
        if finished_setup is not None:
            self.series = [series for series in self.series if id(series) == finished_setup]