import argparse
import os
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/../../')
from Trade.db_util import CChanDB  # noqa: E402
from Trade.TradeEngine import CreateTradeEngine  # noqa: E402


def fix_db(area, is_cover):
    trade_engine = CreateTradeEngine(area, CChanDB())
    try:
        trade_engine.fix_db(is_cover)
    except Exception:
        raise
    finally:
        trade_engine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='fix db')
    parser.add_argument('--area', '-a', help='area (cn/hk/us)', required=True)
    parser.add_argument('--is_cover', '-c', help='is cover', action='store_true')

    args = parser.parse_args()
    fix_db(args.area, args.is_cover)
