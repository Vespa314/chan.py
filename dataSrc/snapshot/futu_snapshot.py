from futu import OpenQuoteContext
import sys
# import traceback
try:
    from KLine.CKline_Unit import KLine_Unit
    from dataSrc.CommonStockAPI import CCommonStockApi
    from common.CTime import CTime
    from common.ChanException import CChanException, ErrCode
except Exception:
    sys.path.append('../..')
    from KLine.CKline_Unit import KLine_Unit
    from dataSrc.CommonStockAPI import CCommonStockApi
    from common.CTime import CTime
    from common.ChanException import CChanException, ErrCode


class CFutuSnapshot:
    @classmethod
    def main(cls, quote_ctx, codelist):
        if type(codelist) != list:
            codelist = [codelist]
        try:
            errcode, res = quote_ctx.get_market_snapshot(codelist)
            if errcode != 0:
                raise Exception(f"query futu snapshot fail:{res}")
            _d = {}
            for idx in range(len(res)):
                data = res.iloc[idx]
                year, month, day = data["update_time"].split(" ")[0].split("-")
                try:
                    item_dict = {
                        CCommonStockApi.FIELD_TIME: CTime(int(year), int(month), int(day), 0, 0),
                        CCommonStockApi.FIELD_OPEN: data["open_price"],
                        CCommonStockApi.FIELD_CLOSE: data["last_price"],
                        CCommonStockApi.FIELD_LOW: data["low_price"],
                        CCommonStockApi.FIELD_HIGH: data["high_price"],
                        CCommonStockApi.FIELD_VOLUME: data["volume"],
                        CCommonStockApi.FIELD_TURNOVER: data["turnover"],
                        CCommonStockApi.FIELD_TURNRATE: data["turnover_rate"],
                    }
                    _d[codelist[idx]] = [KLine_Unit(item_dict)]
                except CChanException as e:
                    # print(traceback.format_exc())
                    if e.errcode in [ErrCode.PRICE_BELOW_ZERO, ErrCode.KL_DATA_INVALID]:
                        _d[codelist[idx]] = None
                    else:
                        raise
            return _d
        except Exception:
            raise

    @classmethod
    def query(cls, codelist):
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        res = {}
        start_idx = 0
        try:
            while start_idx < len(codelist):
                res.update(cls.main(quote_ctx, codelist[start_idx:start_idx+20]))
                start_idx += 20
        except Exception:
            raise
        finally:
            quote_ctx.close()
        return res


if __name__ == "__main__":
    print(CFutuSnapshot.query(["HK.09069"]))
