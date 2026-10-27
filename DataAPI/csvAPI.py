import os

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def create_item_dict(data, column_name, *, auto=None):
    raw = dict(zip(column_name, data))
    trading_day = raw.pop('trading_day', None) or None
    return {name: parse_time_column(value, auto=auto, trading_day=trading_day)
            if name == DATA_FIELD.FIELD_TIME else str2float(value)
            for name, value in raw.items()}


def parse_time_column(inp, *, auto=None, trading_day=None):
    return CTime.from_str(inp, auto=auto, trading_day=trading_day)


class CSV_API(CCommonStockApi):
    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=None):
        self.headers_exist = True  # 第一行是否是标题，如果是数据，设置为False
        self.columns = [
            DATA_FIELD.FIELD_TIME,
            DATA_FIELD.FIELD_OPEN,
            DATA_FIELD.FIELD_HIGH,
            DATA_FIELD.FIELD_LOW,
            DATA_FIELD.FIELD_CLOSE,
            # DATA_FIELD.FIELD_VOLUME,
            # DATA_FIELD.FIELD_TURNOVER,
            # DATA_FIELD.FIELD_TURNRATE,
        ]  # 每一列字段
        self.time_column_idx = self.columns.index(DATA_FIELD.FIELD_TIME)
        super(CSV_API, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        cur_path = os.path.dirname(os.path.realpath(__file__))
        k_type = self.k_type.name[2:].lower()
        file_path = f"{cur_path}/../{self.code}_{k_type}.csv"
        if not os.path.exists(file_path):
            raise CChanException(f"file not exist: {file_path}", ErrCode.SRC_DATA_NOT_FOUND)

        columns = list(self.columns)
        begin = CTime.from_str(self.begin_date) if self.begin_date is not None else None
        end = CTime.from_str(self.end_date) if self.end_date is not None else None
        with open(file_path, 'r', encoding='utf-8-sig') as source:
            for line_number, line in enumerate(source):
                data = line.strip().split(",")
                if self.headers_exist and line_number == 0:
                    # An optional final column supplies vendor/exchange trading dates.
                    if data[-1].strip() == 'trading_day' and 'trading_day' not in columns:
                        columns.append('trading_day')
                    continue
                if len(data) != len(columns):
                    raise CChanException(f"file format error: {file_path}", ErrCode.SRC_DATA_FORMAT_ERROR)
                item = create_item_dict(data, columns, auto=not kltype_lt_day(self.k_type))
                time = item[DATA_FIELD.FIELD_TIME]
                # Date-only bounds refer to trading days; datetime bounds to actual time.
                if begin is not None and (time.trading_day < begin.trading_day if begin.auto else time.ts < begin.ts):
                    continue
                if end is not None and (time.trading_day > end.trading_day if end.auto else time.ts > end.ts):
                    continue
                yield CKLine_Unit(item)

    def SetBasciInfo(self):
        pass

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass
