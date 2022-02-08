# https://openapi.futunn.com/futu-api-doc/quote/overview.html
from futu import OpenQuoteContext, KL_FIELD, KLType, SecurityType, Market, AuType
from common.CEnum import KL_TYPE, AUTYPE
from common.CTime import CTime
from .CommonStockAPI import CCommonStockApi
from KLine.CKline_Unit import KLine_Unit


def create_item_dict(df_row, column_name):
    _tmp = {c: df_row[c] for c in column_name}
    _tmp[CFutu_api.FIELD_TURNRATE] *= 100
    return parse_time_column(_tmp)


def parse_time_column(_dict):
    for k in _dict:
        if k != CCommonStockApi.FIELD_TIME:
            continue
        # '2021-09-02 10:00:00'
        year = int(_dict[k][0:4])
        month = int(_dict[k][5:7])
        day = int(_dict[k][8:10])
        hour = int(_dict[k][11:13])
        minute = int(_dict[k][14:16])
        _dict[k] = CTime(year, month, day, hour, minute)
    return _dict


class CFutu_api(CCommonStockApi):
    quote_ctx = None

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CFutu_api, self).__init__(code, k_type, begin_date, end_date, autype)

    @classmethod
    def do_init(cls):
        if cls.quote_ctx is None:
            cls.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

    @classmethod
    def do_close(cls):
        if cls.quote_ctx:
            cls.quote_ctx.close()
            cls.quote_ctx = None

    def get_kl_data(self):
        # 日期说明
        # Start 类型	End 类型	说明
        # str	str	start 和 end 分别为指定的日期
        # None	str	start 为 end 往前 365 天
        # str	None	end 为 start 往后 365 天
        # None	None	start 为当前日期，end 往后 365 天
        # https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html
        query_cnt = 50000
        autype_dict = {AUTYPE.QFQ: AuType.QFQ, AUTYPE.HFQ: AuType.HFQ, AUTYPE.NONE: AuType.NONE}
        ret, data, page_req_key = CFutu_api.quote_ctx.request_history_kline(
            self.code,
            start=self.begin_date,
            end=self.end_date,
            ktype=self.__convert_type(),
            max_count=query_cnt,
            autype=autype_dict[self.autype],
            fields=[
                KL_FIELD.DATE_TIME, KL_FIELD.HIGH, KL_FIELD.OPEN, KL_FIELD.LOW, KL_FIELD.CLOSE, KL_FIELD.TURNOVER_RATE,
                KL_FIELD.TRADE_VOL, KL_FIELD.TRADE_VAL
            ])
        if ret != 0:
            raise Exception("获取富途数据失败，失败原因：", data)
        column_name = [
            CFutu_api.FIELD_TIME, CFutu_api.FIELD_OPEN, CFutu_api.FIELD_HIGH, CFutu_api.FIELD_LOW,
            CFutu_api.FIELD_CLOSE, CFutu_api.FIELD_VOLUME, CFutu_api.FIELD_TURNOVER, CFutu_api.FIELD_TURNRATE
        ]

        for idx in range(len(data)):
            yield KLine_Unit(create_item_dict(data.iloc[idx], column_name))

    def SetBasciInfo(self):
        # https://openapi.futunn.com/futu-api-doc/quote/get-static-info.html
        ret, data = self.quote_ctx.get_stock_basicinfo(Market.NONE, SecurityType.NONE, self.code)
        if ret != 0:
            raise Exception("获取基础数据失败，失败原因：", data)
        self.name = data.iloc[0]["name"]
        self.is_stock = data.iloc[0]["stock_type"] != SecurityType.IDX

    def __convert_type(self):
        _dict = {}
        for x in KL_TYPE:
            type_str = str(x).split(".")[1]
            _dict[x] = eval(f"KLType.{type_str}")
        return _dict[self.k_type]


if __name__ == "__main__":
    a = KLType.K_DAY
    s = CFutu_api('HK.00700', KL_TYPE.K_DAY, '2020-05-01', '2020-07-25')
    print(s.name, s.type)
    for kl in s.get_kl_data():
        print(kl)
