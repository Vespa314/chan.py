# -*- coding: utf-8 -*-
"""
Akshare 数据API模块 - 使用 akshare 库获取A股K线数据

Java 开发者注意：
- Python 的 isinstance(val, pd.Timestamp) 检查对象是否为 pandas 时间戳类型
  Java 对比：类似于 Java 的 val instanceof LocalDateTime
- Python 的 df.iterrows() 迭代 DataFrame 的每一行，返回 (index, row)
  Java 对比：Java 没有 DataFrame，类似迭代 List<Map> 或 ResultSet
- Python 的 _ 变量名表示不使用该值，即 for _, row in df.iterrows() 忽略索引
  Java 对比：Java 没有这种约定，通常直接不命名变量
- Python 的 row.get('成交额', 0) 字典取值带默认值
  Java 对比：map.getOrDefault("成交额", 0)
- Python 的 str.startswith('sh') 检查字符串是否以指定前缀开头
  Java 对比：str.startsWith("sh")
"""

import akshare as ak
import pandas as pd

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def create_item_dict(row, autype):
    """
    将 DataFrame 行转换为 K 线单元所需的字典格式

    参数:
        row: DataFrame 的一行数据（pd.Series 或类似字典的对象）
        autype: 复权类型

    返回:
        {DATA_FIELD: 值} 字典

    处理逻辑：
    1. 解析日期（支持多种格式）
    2. 提取 OHLCV 数据
    3. 可选提取换手率
    """
    item = {}

    # 解析日期 - 处理多种格式
    date_val = row['日期']
    if isinstance(date_val, pd.Timestamp):
        year, month, day = date_val.year, date_val.month, date_val.day
    elif isinstance(date_val, str):
        date_str = date_val
        if len(date_str) == 10:  # 格式: 2021-09-13
            year = int(date_str[:4])
            month = int(date_str[5:7])
            day = int(date_str[8:10])
        else:  # 格式: 20210913
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
    else:
        # 尝试转换其他类型
        date_str = str(date_val)[:10]
        year = int(date_str[:4])
        month = int(date_str[5:7])
        day = int(date_str[8:10])

    # 构建K线数据字典
    item[DATA_FIELD.FIELD_TIME] = CTime(year, month, day, 0, 0)
    item[DATA_FIELD.FIELD_OPEN] = str2float(row['开盘'])
    item[DATA_FIELD.FIELD_HIGH] = str2float(row['最高'])
    item[DATA_FIELD.FIELD_LOW] = str2float(row['最低'])
    item[DATA_FIELD.FIELD_CLOSE] = str2float(row['收盘'])
    item[DATA_FIELD.FIELD_VOLUME] = str2float(row['成交量'])
    item[DATA_FIELD.FIELD_TURNOVER] = str2float(row.get('成交额', 0))

    # 换手率可能不存在，存在时才添加
    if '换手率' in row:
        item[DATA_FIELD.FIELD_TURNRATE] = str2float(row['换手率'])

    return item


class CAkshare(CCommonStockApi):
    """
    Akshare 数据源实现 - 使用 akshare 库获取A股数据

    Akshare 是一个开源的金融数据接口，支持多种金融数据源。
    相比 BaoStock，Akshare 不需要登录，但只支持日线级别。

    参数:
        code: 股票代码（如 "600000" 或 "sh600000"）
        k_type: K线周期
        begin_date: 起始日期
        end_date: 结束日期
        autype: 复权类型
    """

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CAkshare, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        获取K线数据（生成器）

        返回:
            CKLine_Unit 的迭代器

        处理逻辑：
        1. 根据复权类型和周期类型转换参数
        2. 个股：使用 ak.stock_zh_a_hist() 获取数据
        3. 指数：使用 ak.stock_zh_index_daily() 获取数据
        4. 逐行遍历 DataFrame，用 yield 返回 CKLine_Unit

        注意：Akshare 目前只支持日线/周线/月线，不支持分钟级别。
        """
        # 转换复权类型
        adjust_dict = {
            AUTYPE.QFQ: "qfq",
            AUTYPE.HFQ: "hfq",
            AUTYPE.NONE: ""
        }
        adjust = adjust_dict.get(self.autype, "qfq")

        # 转换周期类型
        period = self.__convert_type()

        # 格式化日期（去掉 - 分隔符）
        start_date = self.begin_date.replace("-", "") if self.begin_date else "19900101"
        end_date = self.end_date.replace("-", "") if self.end_date else "20991231"

        # 获取数据
        if self.is_stock:
            # 个股数据：使用 akshare 的 stock_zh_a_hist 接口
            df = ak.stock_zh_a_hist(
                symbol=self.code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                timeout=15,
            )
        else:
            # 指数数据：使用 akshare 的 stock_zh_index_daily 接口
            df = ak.stock_zh_index_daily(symbol=self.code)
            # 筛选日期范围并重命名列
            df['日期'] = df['date'].astype(str)
            df = df.rename(columns={
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量'
            })
            if 'amount' in df.columns:
                df['成交额'] = df['amount']
            else:
                df['成交额'] = 0
            df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]

        # 遍历每一行生成K线单元
        # _ 是 Python 约定，表示不使用的变量（这里忽略行索引）
        for _, row in df.iterrows():
            yield CKLine_Unit(create_item_dict(row, self.autype))

    def SetBasciInfo(self):
        """
        设置基本信息

        判断逻辑：
        - 以 sh/sz 开头且数字部分以 000/399 开头 → 指数
        - 其他情况 → 个股
        """
        self.name = self.code
        # 判断是否为指数: sh000001, sz399001 等
        if self.code.startswith('sh') or self.code.startswith('sz'):
            code_num = self.code[2:]  # 去掉前缀
            # 指数代码通常以 000, 399 开头
            if code_num.startswith('000') or code_num.startswith('399'):
                self.is_stock = False
            else:
                self.is_stock = True
        else:
            # 纯数字代码默认为股票
            self.is_stock = True

    @classmethod
    def do_init(cls):
        """初始化 (akshare不需要登录)"""
        pass

    @classmethod
    def do_close(cls):
        """关闭 (akshare不需要登出)"""
        pass

    def __convert_type(self):
        """
        转换K线周期类型为 akshare 格式

        返回:
            akshare 的周期字符串（'daily', 'weekly', 'monthly'）

        注意：Akshare 不支持分钟级别数据
        """
        _dict = {
            KL_TYPE.K_DAY: 'daily',
            KL_TYPE.K_WEEK: 'weekly',
            KL_TYPE.K_MON: 'monthly',
        }
        if self.k_type not in _dict:
            raise Exception(f"akshare不支持{self.k_type}级别的K线数据")
        return _dict[self.k_type]