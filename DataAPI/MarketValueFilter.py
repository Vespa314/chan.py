import os
import random
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
try:
    from Common.ChanException import CChanException, ErrCode
    from Config.EnvConfig import Env
except Exception:
    sys.path.append(f'{cur_path}/..')
    from Common.ChanException import CChanException, ErrCode
    from Config.EnvConfig import Env


class CMarketValueFilter:
    def __init__(self):
        self._marketvalue = {}

        for line in open(f"{Env.Data['stock_info_path']}/market_value_percentile"):
            line = line.strip("\n")
            code, _, p = line.split(",")
            self._marketvalue[code] = float(p)

        self._tradeinfo = {}
        for line in open(f"{Env.Data['stock_info_path']}/tradeinfo_percentile"):
            line = line.strip("\n")
            code, _, _, _, _, _, _, volume_percentile, amount_percentile, rate_percentile, volume_median, amount_median, rate_median = line.split(",")
            self._tradeinfo[code] = {
                'volumn': float(volume_median),
                'amount': float(amount_median),
                'rate': float(rate_median),
            }

    def check_market_value(self, stock_code: str, market_value: float = None) -> bool:
        if stock_code.startswith("ETFSH") or stock_code.startswith("ETFSZ"):
            return True
        if market_value is None:
            return stock_code in self._marketvalue
        else:
            return stock_code in self._marketvalue and self._marketvalue[stock_code] >= market_value

    def check_tradeinfo(self, stock_code: str, metric: dict) -> bool:
        if stock_code not in self._tradeinfo:
            return False
        return all(self._tradeinfo[stock_code][info] >= thred for info, thred in metric.items())

    def GetTradeInfo(self, stock_code: str, metric: str):
        return self._tradeinfo.get(stock_code, {}).get(metric, None)

    def random_stock(self, area=None):
        if code_name := [code for code in self._marketvalue.keys() if area is None or code.startswith("{area}.")]:
            return code_name[int(random.random()*len(code_name))]
        else:
            raise CChanException(f"no valid stock in area={area}", ErrCode.COMMON_ERROR)


# if __name__ == "__main__":
#     sys.path.append(f'{cur_path}/..')from
#     from Config.EnvConfig import Env  # noqa: E402
#     f = CMarketValueFilter()
#     data_path = f'{Env.OFFLINE_DATA_PATH}/d_qfq/'
#     for file_name in os.listdir(data_path):
#         code = file_name.split("-")[0]
#         name = file_name.split('-', 1)[1].rsplit('.', 1)[0]
#         # if not f.check_market_value(code):
#         #     print(code, name)
#         if f.check_tradeinfo(code, 'volumn', 0.95):
#             print(code, name)
