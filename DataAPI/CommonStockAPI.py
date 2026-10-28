# -*- coding: utf-8 -*-
"""
数据API抽象基类模块 - 定义股票数据源的统一接口

Java 开发者注意：
- abc.abstractmethod 是 Python 的抽象方法装饰器，类似于 Java 的 abstract 关键字
  Java 对比：Python 的 @abc.abstractmethod 需要 abc.ABC 或 abc.ABCMeta 元类配合
- @classmethod 是类方法装饰器，第一个参数是类本身(cls)而非实例
  Java 对比：类似于 Java 的 static 方法，但 cls 可以访问类属性和子类
- Iterable[CKLine_Unit] 是泛型类型提示，表示可迭代的 CKLine_Unit 序列
  Java 对比：类似于 Java 的 Iterable<CKLine_Unit>
- Python 的 pass 是空语句占位符，类似于 Java 的空方法体 {}
  Python 需要 pass 是因为缩进语法要求必须有至少一条语句
"""

import abc
from typing import Iterable

from KLine.KLine_Unit import CKLine_Unit


class CCommonStockApi:
    """
    股票数据API抽象基类 - 所有数据源必须继承此类

    参数:
        code: 股票/交易品种代码
        k_type: K线周期类型（日线/周线/月线/分钟线等）
        begin_date: 数据起始日期
        end_date: 数据结束日期
        autype: 复权类型（前复权/后复权/不复权）

    子类需要实现：
    - get_kl_data(): 获取K线数据的迭代器
    - SetBasciInfo(): 设置股票基本信息（名称、是否个股等）
    - do_init(): 类级别初始化（如登录）
    - do_close(): 类级别清理（如登出）

    缠论知识 - 数据源：
    缠论分析需要K线数据，数据源可以是：
    - BaoStock（免费A股数据）
    - Akshare（免费A股数据）
    - CSV 文件（自定义数据）
    - CCXT（加密货币数据）
    - 自定义数据源（继承此类实现）
    """

    def __init__(self, code, k_type, begin_date, end_date, autype):
        self.code = code
        self.name = None         # 股票名称
        self.is_stock = None     # 是否是个股（而非指数）
        self.k_type = k_type
        self.begin_date = begin_date
        self.end_date = end_date
        self.autype = autype
        self.SetBasciInfo()      # 子类实现，设置 name 和 is_stock

    @abc.abstractmethod
    def get_kl_data(self) -> Iterable[CKLine_Unit]:
        """
        获取K线数据的迭代器

        返回:
            CKLine_Unit 的可迭代对象（通常使用 yield 生成器）

        每个 CKLine_Unit 代表一根K线，包含 OHLCV 数据。

        Python 特性：Iterable 表示可迭代对象，可以用 yield 实现
        Java 对比：类似于返回 Iterator<CKLine_Unit> 或 Stream<CKLine_Unit>
        """
        pass

    @abc.abstractmethod
    def SetBasciInfo(self):
        """
        设置股票基本信息

        子类需要设置 self.name 和 self.is_stock
        """
        pass

    @classmethod
    @abc.abstractmethod
    def do_init(cls):
        """
        类级别初始化（静态方法）

        用于数据源的初始化操作，如登录、建立连接等。
        每个类只执行一次初始化。

        Python 特性：@classmethod 表示类方法，cls 是类本身
        Java 对比：类似于 Java 的 static synchronized 初始化方法
        """
        pass

    @classmethod
    @abc.abstractmethod
    def do_close(cls):
        """
        类级别清理（静态方法）

        用于数据源的清理操作，如登出、关闭连接等。

        Python 特性：@classmethod 可以被子类继承和重写
        Java 对比：类似于 Java 的 static void cleanup()
        """
        pass