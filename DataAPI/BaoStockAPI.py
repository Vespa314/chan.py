# -*- coding: utf-8 -*-
"""
BaoStock 数据API模块 - 使用 baostock 库获取A股K线数据

Java 开发者注意：
- Python 的 for i in range(len(data)) 类似于 Java 的 for (int i = 0; i < data.length; i++)
- Python 的 dict(zip(key_list, value_list)) 将两个列表合并为字典
  Java 对比：没有直接对应，需要手动循环或使用 Stream API
- Python 字符串切片 s[:4] 取前4个字符，s[5:7] 取第5-6个字符
  Java 对比：s.substring(0, 4), s.substring(5, 7)
- Python 的 int(s) 字符串转整数，类似于 Java 的 Integer.parseInt(s)
- Python 的 super(ClassName, self).__init__(...) 是 Python 2 兼容写法
  Python 3 可简写为 super().__init__(...)
- Python 类属性 is_connect = None 是类级别的共享属性
  Java 对比：类似于 Java 的 static 字段
"""

import baostock as bs

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def create_item_dict(data, column_name):
    """
    将数据行转换为字典格式

    参数:
        data: 一行数据列表（字符串格式）
        column_name: 列名列表

    返回:
        {字段名: 值} 字典

    处理逻辑：
    1. 第一列（时间）需要特殊解析
    2. 其余列转为浮点数
    3. 用 zip 将列名和值配对成字典
    """
    for i in range(len(data)):
        data[i] = parse_time_column(data[i]) if i == 0 else str2float(data[i])
    return dict(zip(column_name, data))


def parse_time_column(inp):
    """
    解析时间字符串，支持多种格式

    支持的格式：
    - 10位：2021-09-13（日线日期）
    - 17位：20210902113000000（分钟线时间，无分隔符）
    - 19位：2021-09-13 11:30:00（分钟线时间，有分隔符）

    返回:
        CTime 时间对象
    """
    # 20210902113000000
    # 2021-09-13
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
        raise Exception(f"unknown time column from baostock:{inp}")
    return CTime(year, month, day, hour, minute)


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
        "date": DATA_FIELD.FIELD_TIME,
        "open": DATA_FIELD.FIELD_OPEN,
        "high": DATA_FIELD.FIELD_HIGH,
        "low": DATA_FIELD.FIELD_LOW,
        "close": DATA_FIELD.FIELD_CLOSE,
        "volume": DATA_FIELD.FIELD_VOLUME,
        "amount": DATA_FIELD.FIELD_TURNOVER,
        "turn": DATA_FIELD.FIELD_TURNRATE,
    }
    return [_dict[x] for x in fileds.split(",")]


class CBaoStock(CCommonStockApi):
    """
    BaoStock 数据源实现 - 使用 baostock 库获取A股数据

    BaoStock 是一个免费的A股数据接口，提供日线/周线/月线/分钟线数据。
    需要先调用 bs.login() 登录，使用完毕后调用 bs.logout() 登出。

    参数:
        code: 股票代码（如 "sh.600000"）
        k_type: K线周期
        begin_date: 起始日期
        end_date: 结束日期
        autype: 复权类型

    Python 特性：类属性 is_connect 是所有实例共享的
    Java 对比：类似于 Java 的 static Boolean isConnected
    """

    is_connect = None  # 类级别属性，记录登录状态

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CBaoStock, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        获取K线数据（生成器）

        返回:
            CKLine_Unit 的迭代器

        处理逻辑：
        1. 天级别以上：获取完整 OHLCV 数据
        2. 分钟级别：只获取 OHLC 数据（分钟线没有成交量和成交额）
        3. 根据复权类型设置 adjustflag 参数
        4. 逐行读取数据，用 yield 返回

        Python 特性：yield 生成器，逐条返回数据而不是一次性返回列表
        Java 对比：Java 无 yield，需要实现 Iterator 接口或使用 Stream
        """
        # 天级别以上才有详细交易信息（成交量、成交额、换手率）
        if kltype_lt_day(self.k_type):
            if not self.is_stock:
                raise Exception("没有获取到数据，注意指数是没有分钟级别数据的！")
            fields = "time,open,high,low,close"
        else:
            fields = "date,open,high,low,close,volume,amount,turn"

        # 复权类型映射
        autype_dict = {AUTYPE.QFQ: "2", AUTYPE.HFQ: "1", AUTYPE.NONE: "3"}

        # 调用 baostock 查询历史K线数据
        rs = bs.query_history_k_data_plus(
            code=self.code,
            fields=fields,
            start_date=self.begin_date,
            end_date=self.end_date,
            frequency=self.__convert_type(),
            adjustflag=autype_dict[self.autype],
        )
        if rs.error_code != '0':
            raise Exception(rs.error_msg)

        # 逐行读取数据
        # rs.next() 移动到下一行，类似于 Java ResultSet.next()
        while rs.error_code == '0' and rs.next():
            yield CKLine_Unit(create_item_dict(rs.get_row_data(), GetColumnNameFromFieldList(fields)))

    def SetBasciInfo(self):
        """
        设置股票基本信息

        通过 baostock 查询股票基本信息，获取：
        - name: 股票名称
        - is_stock: 是否是个股（stock_type == '1' 表示个股）
        """
        rs = bs.query_stock_basic(code=self.code)
        if rs.error_code != '0':
            raise Exception(rs.error_msg)
        # 返回值：code, code_name, ipoDate, outDate, stock_type, status
        code, code_name, ipoDate, outDate, stock_type, status = rs.get_row_data()
        self.name = code_name
        self.is_stock = (stock_type == '1')  # '1' 表示个股，其他表示指数

    @classmethod
    def do_init(cls):
        """
        类级别初始化 - 登录 baostock

        Python 特性：@classmethod 第一个参数是 cls（类本身）
        Java 对比：类似于 static synchronized void init()
        """
        if not cls.is_connect:
            cls.is_connect = bs.login()

    @classmethod
    def do_close(cls):
        """
        类级别清理 - 登出 baostock

        Python 特性：将 cls.is_connect 设为 None 表示未连接
        Java 对比：类似于 static void close() { isConnected = false; }
        """
        if cls.is_connect:
            bs.logout()
            cls.is_connect = None

    def __convert_type(self):
        """
        转换K线周期类型为 baostock 格式

        返回:
            baostock 的周期字符串（'d', 'w', 'm', '5', '15', '30', '60'）
        """
        _dict = {
            KL_TYPE.K_DAY: 'd',
            KL_TYPE.K_WEEK: 'w',
            KL_TYPE.K_MON: 'm',
            KL_TYPE.K_5M: '5',
            KL_TYPE.K_15M: '15',
            KL_TYPE.K_30M: '30',
            KL_TYPE.K_60M: '60',
        }
        return _dict[self.k_type]