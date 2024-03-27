from datetime import datetime

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from DataAPI.CommonStockAPI import CCommonStockApi
import akshare as ak
import re


def create_item_dict(data, column_name):
    for i in range(len(data)):
        # data[i] = parse_time_column(data[i]) if i == 0 else str2float(data[i])
        data.iloc[i] = parse_time_column(str(data.iloc[i])) if i == 0 else str2float(data.iloc[i])
    return dict(zip(column_name, data))


def parse_time_column(inp):
    # 20210902113000000
    # 2021-09-13
    # 20210313
    if len(inp) == 8:
        year = int(inp[:4])
        month = int(inp[4:6])
        day = int(inp[6:8])
        hour = minute = 0
    elif len(inp) == 10:
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
        raise Exception(f"unknown time column from tushare:{inp}")
    return CTime(year, month, day, hour, minute)


def GetColumnNameFromFieldList(fileds: str):
    # "日期,开盘,收盘,最高,最低,成交量,成交额,换手率"
    _dict = {
        "trade_time": DATA_FIELD.FIELD_TIME,
        "trade_date": DATA_FIELD.FIELD_TIME,
        "open": DATA_FIELD.FIELD_OPEN,
        "high": DATA_FIELD.FIELD_HIGH,
        "low": DATA_FIELD.FIELD_LOW,
        "close": DATA_FIELD.FIELD_CLOSE,
        "vol": DATA_FIELD.FIELD_VOLUME,
        "amount": DATA_FIELD.FIELD_TURNOVER,
        "turn": DATA_FIELD.FIELD_TURNRATE,
        "时间": DATA_FIELD.FIELD_TIME,
        "日期": DATA_FIELD.FIELD_TIME,
        "开盘": DATA_FIELD.FIELD_OPEN,
        "收盘": DATA_FIELD.FIELD_CLOSE,
        "最高": DATA_FIELD.FIELD_HIGH,
        "最低": DATA_FIELD.FIELD_LOW,
        "成交量": DATA_FIELD.FIELD_VOLUME,
        "成交额": DATA_FIELD.FIELD_TURNOVER,
        "换手率": DATA_FIELD.FIELD_TURNRATE,
    }
    return [_dict[x] for x in fileds.split(",")]


def extract_stock_code(code):
    pattern = r'([a-zA-Z]{2}\.)(\d{6})(?:\.\w+)?$|(\d{6})(\.[a-zA-Z]{2})$|^(\d{6})$'
    match = re.search(pattern, code)

    if match:
        # 匹配成功，提取数字部分
        stock_code = match.group(2) or match.group(3) or match.group(5)
        return stock_code
    else:
        return None


class CAKShare(CCommonStockApi):
    is_connect = None

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CAKShare, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):

        autype_dict = {AUTYPE.QFQ: "qfq", AUTYPE.HFQ: "hfq", AUTYPE.NONE: "None"}

        # 天级别以上才有详细交易信息
        df = None
        if kltype_lt_day(self.k_type):
            if not self.is_stock:
                raise Exception("没有获取到数据，注意指数是没有分钟级别数据的！")
            fields = "时间,开盘,收盘,最高,最低,成交量,成交额,换手率"
            df = ak.stock_zh_a_hist_min_em(symbol=self.code,
                                           start_date=parse_time_column(self.begin_date).toDateStr("-"),
                                           # end_date="2021-09-06 09:32:00",
                                           period=self.__convert_type(), adjust=autype_dict[self.autype])
        else:
            fields = "日期,开盘,收盘,最高,最低,成交量,成交额,换手率"
            df = ak.stock_zh_a_hist(symbol=self.code, period=self.__convert_type(), start_date=self.begin_date,
                                    # end_date=self.end_date,
                                    adjust=autype_dict[self.autype])

        columns_to_drop = ["振幅", "涨跌幅", "涨跌额"]
        for column in columns_to_drop:
            if column in df.columns:
                df = df.drop(columns=[column])

        for index, row in df.iterrows():
            yield CKLine_Unit(create_item_dict(row, GetColumnNameFromFieldList(fields)))

    def SetBasciInfo(self):
        self.code = extract_stock_code(self.code)

        self.is_stock = True

        # 转时间格式
        if self.begin_date:
            self.begin_date = datetime.strptime(self.begin_date, "%Y-%m-%d").strftime('%Y%m%d')
        if self.end_date:
            self.end_date = datetime.strptime(self.end_date, "%Y-%m-%d").strftime('%Y%m%d')

    @classmethod
    def do_init(cls):
        ...

    # cls.is_connect = bs.login()

    @classmethod
    def do_close(cls):
        ...

    def __convert_type(self):
        _dict = {
            KL_TYPE.K_DAY: 'daily',
            KL_TYPE.K_WEEK: 'weekly',
            KL_TYPE.K_MON: 'monthly',
            KL_TYPE.K_5M: '5',
            KL_TYPE.K_15M: '15',
            KL_TYPE.K_30M: '30',
            KL_TYPE.K_60M: '60',
        }
        return _dict[self.k_type]
