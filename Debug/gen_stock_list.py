# -*- coding: utf-8 -*-
"""
枚举全部 A 股股票，生成 download_kl.py / intraday_poll.py 的批量灌数配置。

数据源：BaoStock `bs.query_all_stock(day)`（返回 code/tradeStatus/code_name，
含指数/B股，需按代码前缀过滤出 A 股个股）。

用法（需能访问 BaoStock）：
    PYTHONPATH=. python Debug/gen_stock_list.py                         # 生成全部 A 股个股（K_DAY/QFQ）
    PYTHONPATH=. python Debug/gen_stock_list.py --kl-types K_DAY,K_60M --autypes QFQ,HFQ
    PYTHONPATH=. python Debug/gen_stock_list.py --include-index         # 含指数（指数仅日线）
    PYTHONPATH=. python Debug/gen_stock_list.py --limit 20              # 调试：只取前 20 只

生成的文件随后喂给灌数脚本：
    PYTHONPATH=. python Debug/download_kl.py --config <输出文件>
"""

import argparse
import json
import sys
import collections
from datetime import date

# A 股个股代码前缀（过滤掉指数 sh.000/880、B股 sh.900/sz.200 等）
_A_SHARE_PREFIX = {
    "sh": ("600", "601", "603", "605", "688", "689"),
    "sz": ("000", "001", "002", "003", "300", "301", "302"),
    "bj": None,  # 北交所前缀内均为股票，不按数字段过滤
}


def is_a_share_stock(code: str) -> bool:
    """判断是否为 A 股个股（不含指数/基金/B股）。"""
    if not code or "." not in code:
        return False
    exch, num = code.split(".")
    if exch not in _A_SHARE_PREFIX:
        return False
    prefixes = _A_SHARE_PREFIX[exch]
    if prefixes is None:  # bj：全部视为股票
        return True
    return num[:3] in prefixes


def latest_trading_day() -> str:
    """返回最近一个交易日（用于 query_all_stock，避免周末/节假日拿到空结果）。"""
    try:
        import exchange_calendars as xcals
        import pandas as pd

        cal = xcals.get_calendar("XSHG")
        today = pd.Timestamp.now().normalize()
        if cal.is_session(today):
            return today.strftime("%Y-%m-%d")
        sessions = cal.sessions_in_range(today - pd.Timedelta(days=10), today)
        return sessions[-1].strftime("%Y-%m-%d")
    except Exception:
        return date.today().strftime("%Y-%m-%d")


def query_all_a_share(day: str, include_index: bool):
    """返回 [(code, name), ...]，翻页遍历 query_all_stock 全部证券。"""
    import baostock as bs

    bs.login()
    try:
        rs = bs.query_all_stock(day=day)
        if rs.error_code != "0":
            raise RuntimeError(f"query_all_stock 失败：{rs.error_msg}")
        out = []
        while rs.error_code == "0" and rs.next():
            row = rs.get_row_data()
            code, trade_status, code_name = row[0], row[1], row[2]
            if not include_index and not is_a_share_stock(code):
                continue
            out.append((code, code_name))
        return out
    finally:
        bs.logout()


def build_config(stocks, kl_types, autypes, db_path):
    return {
        "db_path": db_path,
        "defaults": {"autype": autypes[0]},
        "poll_interval_seconds": 60,
        "trading_sessions": [["09:30", "11:30"], ["13:00", "15:00"]],
        "stocks": [
            {"code": code, "kl_types": kl_types, "autypes": autypes}
            for code, _name in stocks
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="枚举 A 股并生成灌数配置")
    p.add_argument("--day", default=None, help="查询日期 YYYY-MM-DD（默认最近交易日）")
    p.add_argument("--output", default="Debug/ingest_config.all_stocks.json",
                   help="输出 JSON 路径")
    p.add_argument("--kl-types", default="K_DAY",
                   help="逗号分隔的 K 线级别，如 K_DAY,K_60M")
    p.add_argument("--autypes", default="QFQ", help="逗号分隔的复权类型")
    p.add_argument("--db-path", default="kl_store.duckdb", help="DuckDB 库路径")
    p.add_argument("--include-index", action="store_true",
                   help="包含指数/基金/B股（默认仅 A 股个股）")
    p.add_argument("--limit", type=int, default=None, help="调试用：只取前 N 只")
    args = p.parse_args(argv)

    day = args.day or latest_trading_day()
    kl_types = [x.strip() for x in args.kl_types.split(",") if x.strip()]
    autypes = [x.strip() for x in args.autypes.split(",") if x.strip()]
    if not kl_types or not autypes:
        p.error("--kl-types / --autypes 不能为空")

    print(f"查询交易日：{day}  （include_index={args.include_index}）")
    stocks = query_all_a_share(day, args.include_index)
    if args.limit:
        stocks = stocks[: args.limit]
    print(f"命中证券 {len(stocks)} 只")

    # 交易所分布统计
    dist = collections.Counter(c.split(".")[0] for c, _ in stocks)
    print("交易所分布：", dict(dist))

    cfg = build_config(stocks, kl_types, autypes, args.db_path)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"已写入 {args.output}")
    print(f"随后执行：PYTHONPATH=. python Debug/download_kl.py --config {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
