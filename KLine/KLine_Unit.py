# -*- coding: utf-8 -*-
"""
K线单元模块 - 表示单根 K 线的数据结构和计算

Java 开发者注意：
- Python 的 copy.deepcopy 类似于 Java 中实现 Cloneable 接口 + 深拷贝
- yield from 是 Python 生成器委托语法，类似于 Java 迭代器的 flatMap
- __deepcopy__ 是 Python 的深拷贝钩子方法，类似于 Java 的 clone() 方法
- hasattr(obj, attr) 类似于 Java 反射中的 obj.getClass().getField("attr") != null
- Python 的 @property 装饰器把方法变成属性访问，类似于 Java 的 getter 但语法不同
"""

import copy
from typing import Dict, Optional

from Common.CEnum import DATA_FIELD, TRADE_INFO_LST, TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Math.BOLL import BOLL_Metric, BollModel
from Math.Demark import CDemarkEngine, CDemarkIndex
from Math.KDJ import KDJ
from Math.MACD import CMACD, CMACD_item
from Math.RSI import RSI
from Math.TrendModel import CTrendModel

from .TradeInfo import CTradeInfo


class CKLine_Unit:
    """
    单根K线单元 - 存储 K 线的价格、时间、指标等数据

    这是整个缠论分析系统中最基础的数据单元。每根 K 线包含：
    - OHLC 价格数据（开/高/低/收）
    - 时间信息
    - 技术指标（MACD、BOLL、RSI、KDJ、Demark、Trend）
    - 父子级别关系（sub_kl_list、sup_kl）
    - 所属合并K线引用（__klc）

    属性说明：
    - time: K线时间
    - open/close/high/low: OHLC 价格数据
    - trade_info: 交易信息（成交量、成交额、换手率）
    - sub_kl_list: 次级别K线列表（多级别递归时使用）
    - sup_kl: 指向父级别K线（多级别递归时使用）
    - __klc: 指向所属的合并K线（CKLine）
    - macd/boll/rsi/kdj: 各技术指标值
    - demark: Demark 序列指标
    - trend: 均线趋势数据
    - limit_flag: 涨跌停标记（0=普通，-1=跌停，1=涨停）
    - pre/next: 前后K线指针（链表结构）
    """

    def __init__(self, kl_dict, autofix=False):
        """
        初始化K线单元
        参数:
            kl_dict: 字典，包含 OHLC 价格和交易信息
            autofix: 是否自动修复异常数据（high < low 等情况）
        Python 特性：字典参数解构，类似于 Java 的 Map<String, Object>
        Java 对比：没有构造函数重载，用默认参数 autofix=False 实现
        """
        self.kl_type = None
        self.time: CTime = kl_dict[DATA_FIELD.FIELD_TIME]
        self.close = kl_dict[DATA_FIELD.FIELD_CLOSE]
        self.open = kl_dict[DATA_FIELD.FIELD_OPEN]
        self.high = kl_dict[DATA_FIELD.FIELD_HIGH]
        self.low = kl_dict[DATA_FIELD.FIELD_LOW]

        self.check(autofix)  # 数据有效性校验

        self.trade_info = CTradeInfo(kl_dict)

        self.demark: CDemarkIndex = CDemarkIndex()

        self.sub_kl_list = []  # 次级别KLU列表
        self.sup_kl: Optional[CKLine_Unit] = None  # 指向更高级别KLU

        from KLine.KLine import CKLine
        self.__klc: Optional[CKLine] = None  # 指向合并K线

        self.trend: Dict[TREND_TYPE, Dict[int, float]] = {}  # 均线趋势数据

        self.limit_flag = 0  # 0:普通 -1:跌停，1:涨停
        self.pre: Optional[CKLine_Unit] = None  # 前一根K线
        self.next: Optional[CKLine_Unit] = None  # 后一根K线

        self.set_idx(-1)

    def __deepcopy__(self, memo):
        """
        深拷贝钩子方法
        参数:
            memo: 拷贝备忘录字典，防止循环引用导致无限递归
        返回:
            新的 CKLine_Unit 实例
        Python 特性：__deepcopy__ 是 copy.deepcopy 的回调钩子
        Java 对比：类似于实现 Cloneable 接口并重写 clone() 方法
        注意：这里通过重建 __dict__ + 重新构造的方式实现深拷贝，而不是直接复制属性
        """
        # 重新构建原始字典，用于重新创建 CKLine_Unit
        _dict = {
            DATA_FIELD.FIELD_TIME: self.time,
            DATA_FIELD.FIELD_CLOSE: self.close,
            DATA_FIELD.FIELD_OPEN: self.open,
            DATA_FIELD.FIELD_HIGH: self.high,
            DATA_FIELD.FIELD_LOW: self.low,
        }
        for metric in TRADE_INFO_LST:
            if metric in self.trade_info.metric:
                _dict[metric] = self.trade_info.metric[metric]
        obj = CKLine_Unit(_dict)
        # 深拷贝各子对象
        obj.demark = copy.deepcopy(self.demark, memo)
        obj.trend = copy.deepcopy(self.trend, memo)
        obj.limit_flag = self.limit_flag
        obj.macd = copy.deepcopy(self.macd, memo)
        obj.boll = copy.deepcopy(self.boll, memo)
        if hasattr(self, "rsi"):
            obj.rsi = copy.deepcopy(self.rsi, memo)
        if hasattr(self, "kdj"):
            obj.kdj = copy.deepcopy(self.kdj, memo)
        obj.set_idx(self.idx)
        memo[id(self)] = obj  # 记录到备忘录，防止重复拷贝
        # Python 特性：id(self) 返回对象的内存地址，类似于 Java 的 System.identityHashCode()
        return obj

    @property
    def klc(self):
        """
        获取所属的合并K线（CKLine）
        如果为 None 则断言失败
        Python 特性：@property 把方法调用变成属性访问语法
        Java 对比：类似于 getKlc() 但调用时不需要括号
        """
        assert self.__klc is not None
        return self.__klc

    def set_klc(self, klc):
        """设置所属的合并K线引用"""
        self.__klc = klc

    @property
    def idx(self):
        """获取K线索引"""
        return self.__idx

    def set_idx(self, idx):
        """设置K线索引"""
        self.__idx: int = idx

    def __str__(self):
        """
        字符串表示
        Python 特性：__str__ 类似于 Java 的 toString() 方法
        Python 语法：f-string 类似于 Java 的 String.format() 但更简洁
        """
        return f"{self.idx}:{self.time}/{self.kl_type} open={self.open} close={self.close} high={self.high} low={self.low} {self.trade_info}"

    def check(self, autofix=False):
        """
        校验 K 线数据有效性
        参数:
            autofix: 是否自动修复（True=修复，False=抛异常）
        检查逻辑：
        - low 必须是四个价格中的最小值
        - high 必须是四个价格中的最大值
        如果 autofix=True，自动将异常值修复为正确的 min/max
        """
        if self.low > min([self.low, self.open, self.high, self.close]):
            if autofix:
                self.low = min([self.low, self.open, self.high, self.close])
            else:
                raise CChanException(f"{self.time} low price={self.low} is not min of [low={self.low}, open={self.open}, high={self.high}, close={self.close}]", ErrCode.KL_DATA_INVALID)
        if self.high < max([self.low, self.open, self.high, self.close]):
            if autofix:
                self.high = max([self.low, self.open, self.high, self.close])
            else:
                raise CChanException(f"{self.time} high price={self.high} is not max of [low={self.low}, open={self.open}, high={self.high}, close={self.close}]", ErrCode.KL_DATA_INVALID)

    def add_children(self, child):
        """
        添加子级别K线
        参数:
            child: 子级别 CKLine_Unit
        使用场景：多级别递归时，高级别K线包含多个低级别K线
        """
        self.sub_kl_list.append(child)

    def set_parent(self, parent: 'CKLine_Unit'):
        """
        设置父级别K线
        参数:
            parent: 父级别 CKLine_Unit
        使用场景：多级别递归时，低级别K线指向其所属的高级别K线
        """
        self.sup_kl = parent

    def get_children(self):
        """
        获取所有子级别K线的迭代器
        Python 语法：yield from 是生成器委托，逐个产出子列表中的元素
        Java 对比：类似于 Java 中 Iterable.iterator() 的 flatMap 操作
        """
        yield from self.sub_kl_list

    def _low(self):
        """获取最低价（内部方法，统一接口用）"""
        return self.low

    def _high(self):
        """获取最高价（内部方法，统一接口用）"""
        return self.high

    def set_metric(self, metric_model_lst: list) -> None:
        """
        设置各项技术指标值

        参数:
            metric_model_lst: 技术指标模型列表，每个元素是一个指标计算器

        遍历所有指标模型，根据类型调用对应的 add/update 方法：
        - CMACD: 计算 MACD 指标（DIF、DEA、MACD柱）
        - CTrendModel: 计算均线趋势（MA、EMA等）
        - BollModel: 计算布林带（上轨、中轨、下轨）
        - CDemarkEngine: 计算 Demark 序列（TD序列）
        - RSI: 计算相对强弱指标
        - KDJ: 计算随机指标

        Python 语法：isinstance(obj, Type) 类似于 Java 的 obj instanceof Type
        """
        for metric_model in metric_model_lst:
            if isinstance(metric_model, CMACD):
                self.macd: CMACD_item = metric_model.add(self.close)
            elif isinstance(metric_model, CTrendModel):
                if metric_model.type not in self.trend:
                    self.trend[metric_model.type] = {}
                self.trend[metric_model.type][metric_model.T] = metric_model.add(self.close)
            elif isinstance(metric_model, BollModel):
                self.boll: BOLL_Metric = metric_model.add(self.close)
            elif isinstance(metric_model, CDemarkEngine):
                self.demark = metric_model.update(idx=self.idx, close=self.close, high=self.high, low=self.low)
            elif isinstance(metric_model, RSI):
                self.rsi = metric_model.add(self.close)
            elif isinstance(metric_model, KDJ):
                self.kdj = metric_model.add(self.high, self.low, self.close)

    def get_parent_klc(self):
        """获取父级别合并K线（通过 sup_kl -> klc 链）"""
        assert self.sup_kl is not None
        return self.sup_kl.klc

    def include_sub_lv_time(self, sub_lv_t: str) -> bool:
        """
        递归检查当前K线（及其子级别K线）是否包含指定时间

        参数:
            sub_lv_t: 要检查的时间字符串

        返回:
            True 如果当前K线或其任何子级别K线包含该时间

        使用场景：多级别K线时间对齐检查，确保父级别K线的时间范围覆盖子级别
        递归逻辑：先检查自身，再递归检查所有子K线
        """
        if self.time.to_str() == sub_lv_t:
            return True
        for sub_klu in self.sub_kl_list:
            if sub_klu.time.to_str() == sub_lv_t:
                return True
            if sub_klu.include_sub_lv_time(sub_lv_t):  # 递归检查子K线的子K线
                return True
        return False

    def set_pre_klu(self, pre_klu: Optional['CKLine_Unit']):
        """
        设置前一根K线的双向链表关系
        参数:
            pre_klu: 前一根K线，如果为 None 则跳过
        行为：同时设置 pre_klu.next = self 和 self.pre = pre_klu
        """
        if pre_klu is None:
            return
        pre_klu.next = self
        self.pre = pre_klu