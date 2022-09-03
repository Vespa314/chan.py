import argparse
import gzip
import os
import sys

import numpy as np
from tqdm import tqdm

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/../../')
from Common.func_util import send_error_if_fail  # noqa: E402
from Common.TradeUtil import GetCodeArea2  # noqa: E402
from Config.EnvConfig import Env  # noqa: E402


def GetTradeInfo(path, cnt):
    content = gzip.open(path, 'rt').read().split("\n")
    res = []
    for item in content[-cnt:]:
        try:
            _list = [float(x) for x in item.split(",")[-3:]]
            res.append(_list)
        except Exception:
            ...
    return res


def _avg(lst):
    return np.array(lst).mean(axis=0)


def _min(lst):
    return np.array(lst).min(axis=0)


def percentile(lst, p=0.5):
    return np.percentile(lst, [p], axis=0)[0]


def save_perc(fid, lst):
    N = len(lst)
    for i in range(3):
        lst.sort(key=lambda x: x[1][i])
        for rank, info in enumerate(lst):
            _r = float(rank+1)/N
            info.append(_r)
        lst.sort(key=lambda x: x[2][i])
        for rank, info in enumerate(lst):
            _r = float(rank+1)/N
            info.append(_r)
    for info in lst:
        fid.write(f"{info[0]},{info[1][0]:.1f},{info[1][1]:.1f},{info[1][2]:.3f},{info[2][0]:.1f},{info[2][1]:.1f},{info[2][2]:.3f},{info[3]:.5f},{info[4]:.5f},{info[5]:.5f},{info[6]:.5f},{info[7]:.5f},{info[8]:.5f}\n")


@send_error_if_fail('cal tradeinfo percentile fail')
def main():
    parser = argparse.ArgumentParser(description='TradeInfo Calculation')
    parser.add_argument('--record_cnt', '-c', help='record_cnt', default=30)
    args = parser.parse_args()

    root_path = f"{Env.OFFLINE_DATA_PATH}/d_qfq/"
    res = {"cn": [], "hk": [], "us": [], "etf": []}
    for file_name in tqdm(os.listdir(root_path)):
        code = file_name.split("-")[0]
        trade_info = GetTradeInfo(f'{root_path}/{file_name}', int(args.record_cnt))
        if not trade_info:
            continue
        res[GetCodeArea2(code)].append([code, _avg(trade_info), percentile(trade_info)])

    with open(f"{Env.Data['stock_info_path']}/tradeinfo_percentile", "w") as fid:
        for metric in res.values():
            save_perc(fid, metric)


if __name__ == "__main__":
    main()
