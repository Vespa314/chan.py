# -*- coding: utf-8 -*-
"""
CSV 数据API模块 - 从本地 CSV 文件读取K线数据

Java 开发者注意：
- Python 的 os.path.dirname(os.path.realpath(__file__)) 获取当前文件所在目录
  Java 对比：类似于 getClass().getResource("/").getPath()
- Python 的 os.path.exists(path) 检查文件是否存在
  Java 对比：类似于 new File(path).exists()
- Python 的 enumerate(iterable) 返回 (索引, 值) 的迭代器
  Java 对比：Java 没有直接对应，通常手动维护计数器
- Python 的 open(file, 'r') 是上下文管理器协议，用 with 语句更安全
  Java 对比：类似于 try-with-resources 的 new BufferedReader(new FileReader(file))
"""

import os

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def create_item_dict(data, column_name):
    """
    将 CSV 行数据转换为字典格式

    参数:
        data: 一行数据列表（字符串格式）
        column_name: 列名列表（DATA_FIELD 枚举）

    返回:
        {字段名: 值} 字典

    处理逻辑：
    1. 时间列：特殊解析为 CTime 对象
    2. 其余列：转为浮点数
    """
    for i in range(len(data)):
        data[i] = parse_time_column(data[i]) if column_name[i] == DATA_FIELD.FIELD_TIME else str2float(data[i])
    return dict(zip(column_name, data))


def parse_time_column(inp):
    """
    解析时间字符串，支持多种格式

    支持的格式：
    - 10位：2021-09-13（有分隔符）
    - 17位：20210902113000000（无分隔符，精确到分钟）
    - 19位：2021-09-13 11:30:00（有完整分隔符）

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
        raise Exception(f"unknown time column from csv:{inp}")
    return CTime(year, month, day, hour, minute)


class CSV_API(CCommonStockApi):
    """
    CSV 文件数据源实现 - 从本地 CSV 文件读取K线数据

    用于导入自定义数据，CSV 文件命名规则：{code}_{k_type}.csv
    例如：600000_day.csv（日线数据）

    参数:
        code: 股票代码（用于定位 CSV 文件名）
        k_type: K线周期
        begin_date: 起始日期过滤
        end_date: 结束日期过滤
        autype: 复权类型（CSV 数据一般不需要复权处理）

    可配置属性：
    - headers_exist: 第一行是否是标题行（默认 True）
    - columns: 每列对应的字段定义
    - time_column_idx: 时间列在 columns 中的索引
    """

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=None):
        self.headers_exist = True  # 第一行是否是标题，如果是数据，设置为 False
        self.columns = [
            DATA_FIELD.FIELD_TIME,
            DATA_FIELD.FIELD_OPEN,
            DATA_FIELD.FIELD_HIGH,
            DATA_FIELD.FIELD_LOW,
            DATA_FIELD.FIELD_CLOSE,
            # 可选字段（默认注释掉，按需取消注释）
            # DATA_FIELD.FIELD_VOLUME,
            # DATA_FIELD.FIELD_TURNOVER,
            # DATA_FIELD.FIELD_TURNRATE,
        ]  # 每一列对应的字段定义
        self.time_column_idx = self.columns.index(DATA_FIELD.FIELD_TIME)
        super(CSV_API, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        获取K线数据（生成器）

        返回:
            CKLine_Unit 的迭代器

        处理逻辑：
        1. 根据 code 和 k_type 定位 CSV 文件
        2. 逐行读取 CSV 文件
        3. 跳过标题行（如果 headers_exist=True）
        4. 按日期范围过滤
        5. 解析每行数据为 CKLine_Unit

        数据格式：CSV 每行用逗号分隔，列顺序与 self.columns 对应
        """
        cur_path = os.path.dirname(os.path.realpath(__file__))
        k_type = self.k_type.name[2:].lower()  # 如 K_DAY → day, K_60M → 60m
        file_path = f"{cur_path}/../{self.code}_{k_type}.csv"
        if not os.path.exists(file_path):
            raise CChanException(f"file not exist: {file_path}", ErrCode.SRC_DATA_NOT_FOUND)

        for line_number, line in enumerate(open(file_path, 'r')):
            if self.headers_exist and line_number == 0:
                continue  # 跳过标题行
            data = line.strip("\n").split(",")
            if len(data) != len(self.columns):
                raise CChanException(f"file format error: {file_path}", ErrCode.SRC_DATA_FORMAT_ERROR)
            # 日期范围过滤
            if self.begin_date is not None and data[self.time_column_idx] < self.begin_date:
                continue
            if self.end_date is not None and data[self.time_column_idx] > self.end_date:
                continue
            yield CKLine_Unit(create_item_dict(data, self.columns))

    def SetBasciInfo(self):
        """CSV 数据源不需要设置基本信息"""
        pass

    @classmethod
    def do_init(cls):
        """CSV 数据源不需要初始化"""
        pass

    @classmethod
    def do_close(cls):
        """CSV 数据源不需要清理"""
        pass