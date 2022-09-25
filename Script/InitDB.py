import os
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/..')
from Config.EnvConfig import Env  # noqa: E402
from Trade.db_util import GetDB  # noqa: E402
from Trade.MysqlDB import CMysqlDB  # noqa: E402
from Trade.SqliteDB import CSqliteDB  # noqa: E402

if __name__ == "__main__":
    db = GetDB()
    table_name = Env.DB['DATABASE']
    if type(db) == CSqliteDB:
        print("creating sqlite db")
        db.query(f"""
create table if not exists {table_name}(
    id INTEGER NOT NULL ,
    add_date timestamp,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    status TEXT NOT NULL,
    lv char(5) NOT NULL,
    bstype char(10) NOT NULL,
    is_buy boolean default true,
    open_thred float,
    sl_thred float,
    target_klu_time TEXT,
    watching boolean default true,
    unwatch_reason TEXT,
    signal_last_modify timestamp,
    model_version TEXT,
    model_score_before float,
    model_score_after float,
    is_open  BOOLEAN default false,
    open_price float,
    quota int default 0,
    open_date timestamp,
    open_order_id TEXT,
    open_image_url TEXT,
    peak_price_after_open float,
    cover_avg_price float,
    cover_quota int default 0,
    cover_date timestamp,
    cover_reason TEXT,
    cover_order_id TEXT,
    open_err boolean default false,
    close_err boolean default false,
    open_err_reason TEXT,
    close_err_reason TEXT,
    relate_cover_id int,
    is_cover_record bool default false,
    PRIMARY KEY (id)
    );""", commit=True)
    elif type(db) == CMysqlDB:
        print("creating mysql db")
        db.query(f"""
create table if not exists {table_name}(
    id int(11) NOT NULL AUTO_INCREMENT,
    add_date datetime(6),  --- 计算信号时
    stock_code varchar(20) NOT NULL,  --- 计算信号时
    stock_name varchar(64) NOT NULL,  --- 计算信号时
    status varchar(20) NOT NULL,
    lv char(5) NOT NULL,  --- 计算信号时
    bstype char(10) NOT NULL,  --- 计算信号时
    is_buy boolean default true,  --- 计算信号时
    open_thred float,  --- 计算信号时
    sl_thred float,  --- 计算信号时
    target_klu_time varchar(10),  --- 计算信号时  【target_klu_time和code作为唯一键值】

    watching boolean default true,  --- 默认为True, 信号不再生效时/修复错误信号时为False
    unwatch_reason varchar(256),  --- 计算信号时不再生效时设置
    signal_last_modify datetime(6),  --- 计算信号时不再生效时设置
    model_version varchar(256), --- 开仓时
    model_score_before float,  --- 开仓时
    model_score_after float,  --- 分数复查时

    is_open  BOOLEAN default false,  --- 开仓信号突破时
    open_price float,  --- 成交时设置
    quota int default 0,  --- 提交订单时
    open_date datetime(6),  --- 开仓信号突破时
    open_order_id varchar(32),  --- 提交订单时
    open_image_url varchar(64),--- 开仓信号突破时
    peak_price_after_open float, --- 更新peak_price时

    cover_avg_price float, -- 平仓成交时
    cover_quota int default 0, --- 平仓提交订单时
    cover_date datetime(6), --- 平仓提交订单时
    cover_reason varchar(256),  ---  or 平仓提交时设置
    cover_order_id varchar(256), --- 平仓提交订单时

    open_err boolean default false,  --- 默认为FALSE, recheck时发现错误信号设置为True
    close_err boolean default false,
    open_err_reason varchar(256),  --- recheck时发现错误信号设置为True
    close_err_reason varchar(256),

    relate_cover_id int, --- 平仓信号突破时设置
    is_cover_record bool default false, --- 开仓时设置
    PRIMARY KEY (id)
    );""", commit=True)
    else:
        raise Exception("unknown db type")
