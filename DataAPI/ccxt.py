# -*- coding: utf-8 -*-
"""
CCXT 数据API模块 - 使用 ccxt 库获取加密货币K线数据

Java 开发者注意：
- Python 的 datetime.fromtimestamp(timestamp / 1000) 将毫秒时间戳转为 datetime 对象
  Java 对比：new Date(timestamp) 或 Instant.ofEpochMilli(timestamp)
- Python 的 time_obj.strftime('%Y-%m-%d %H:%M:%S') 格式化时间
  Java 对比：DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").format(...)
- Python 的 dict(zip(key_list, value_list)) 将两个列表合并为字典
  Java 对比：没有直接对应，需要循环或 Stream API
- Python 的 with 语句是上下文管理器，自动管理资源释放
  Java 对比：try-with-resources 语句
"""

from datetime import datetime

import ccxt

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def GetColumnNameFromFieldList(fileds: str):
    """
    将字段名字符串转换为 DATA_FIELD 枚举列表

    参数:
        fileds: 逗号分隔的字段名，如 "time,open,high,low,close"

    返回:
        DATA_FIELD 枚举值列表
    """
    _dict = {
        "time": DATA_FIELD.FIELD_TIME,
        "open": DATA_FIELD.FIELD_OPEN,
        "high": DATA_FIELD.FIELD_HIGH,
        "low": DATA_FIELD.FIELD_LOW,
        "close": DATA_FIELD.FIELD_CLOSE,
    }
    return [_dict[x] for x in fileds.split(",")]


class CCXT(CCommonStockApi):
    """
    CCXT 数据源实现 - 使用 ccxt 库获取加密货币数据

    CCXT 是一个统一的加密货币交易所API库，支持 100+ 交易所。
    目前此实现使用 Binance 交易所获取数据。

    参数:
        code: 交易对代码（如 "BTC/USDT"）
        k_type: K线周期
        begin_date: 起始日期
        end_date: 结束日期
        autype: 复权类型（加密货币一般不需要复权）
    """

    is_connect = None

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CCXT, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        获取K线数据（生成器）

        返回:
            CKLine_Unit 的迭代器

        处理逻辑：
        1. 创建 Binance 交易所实例
        2. 转换时间周期格式
        3. 调用 fetch_ohlcv() 获取 OHLCV 数据
        4. 逐条解析数据，用 yield 返回

        注意：CCXT 返回的数据格式为 [timestamp, open, high, low, close, volume]
        时间戳是毫秒级的 Unix 时间戳。
        """
        fields = "time,open,high,low,close"
        exchange = ccxt.binance()
        timeframe = self.__convert_type()
        since_date = exchange.parse8601(f'{self.begin_date}T00:00:00')
        data = exchange.fetch_ohlcv(self.code, timeframe, since=since_date)

        for item in data:
            # item[0] 是毫秒时间戳，转为 datetime 再格式化
            time_obj = datetime.fromtimestamp(item[0] / 1000)
            time_str = time_obj.strftime('%Y-%m-%d %H:%M:%S')
            item_data = [
                time_str,
                item[1],  # open
                item[2],  # high
                item[3],  # low
                item[4],  # close
            ]
            # autofix=True 表示自动修复缺失的数据字段
            yield CKLine_Unit(self.create_item_dict(item_data, GetColumnNameFromFieldList(fields)), autofix=True)

    def SetBasciInfo(self):
        """CCXT 数据源不需要设置基本信息"""
        pass

    @classmethod
    def do_init(cls):
        """CCXT 不需要初始化"""
        pass

    @classmethod
    def do_close(cls):
        """CCXT 不需要清理"""
        pass

    def __convert_type(self):
        """
        转换K线周期类型为 CCXT 格式

        返回:
            CCXT 的时间周期字符串（'1d', '1w', '1M', '5m', '15m', '30m', '1h'）
        """
        _dict = {
            KL_TYPE.K_DAY: '1d',
            KL_TYPE.K_WEEK: '1w',
            KL_TYPE.K_MON: '1M',
            KL_TYPE.K_5M: '5m',
            KL_TYPE.K_15M: '15m',
            KL_TYPE.K_30M: '30m',
            KL_TYPE.K_60M: '1h',
        }
        return _dict[self.k_type]

    def parse_time_column(self, inp):
        """
        解析时间字符串

        支持的格式：
        - 10位：2021-09-13
        - 17位：20210902113000000
        - 19位：2021-09-13 11:30:00

        参数:
            inp: 时间字符串

        返回:
            CTime 时间对象

        auto 参数：对于小于日级别的K线，auto=False 表示不自动调整时间
        """
        if len(inp) == 10:
            year = int(inp[:4])
            month = int(inp[5:7])
            day = int(inp[8:10])
            hour = minute = 0
        elif len(inp) == 17:
            year = int(inp[:4])
            month = int(inp[4:6])
            day = int(inp[6:8])
            hour = int(inp[8:10])
            minute = int(inp[10:12])
        elif len(inp) == 19:
            year = int(inp[:4])
            month = int(inp[5:7])
            day = int(inp[8:10])
            hour = int(inp[11:13])
            minute = int(inp[14:16])
        else:
            raise Exception(f"unknown time column from TradingView:{inp}")
        return CTime(year, month, day, hour, minute, auto=not kltype_lt_day(self.k_type))

    def create_item_dict(self, data, column_name):
        """
        将数据行转换为字典格式

        参数:
            data: 一行数据列表
            column_name: 列名列表

        返回:
            {字段名: 值} 字典
        """
        for i in range(len(data)):
            data[i] = self.parse_time_column(data[i]) if i == 0 else str2float(data[i])
        return dict(zip(column_name, data))