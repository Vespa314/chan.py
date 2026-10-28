# -*- coding: utf-8 -*-
"""
策略演示2 - 外部喂K线模式（trigger_load）

Java 开发者注意：
- chan.trigger_load({KL_TYPE.K_DAY: [klu]}) 从外部逐根推送K线
  Java 对比：类似于事件驱动的回调模式，而非内部循环
- 这种模式适用于实时数据场景，每收到一根新K线就触发一次分析
- Python 的 classmethod do_init() 需要通过类名调用：CBaoStock.do_init()
  Java 对比：ClassName.staticMethod()

策略说明：
    与 strategy_demo.py 相同策略，但演示如何从 CChan 外部喂K线来触发内部缠论计算。
    这种模式适用于：
    - 实时行情推送
    - 自定义数据源
    - 与其他系统集成
"""

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock

if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2021-01-01"
    end_time = None
    data_src_type = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": True,
        "divergence_rate": 0.8,
        "min_zs_cnt": 1,
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,     # 在 trigger_load 模式下这些参数已不再使用
        end_time=end_time,         # 数据由外部直接提供
        data_src=data_src_type,    # 仅用于类型标识
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,         # 数据由外部提供，复权类型不再生效
    )

    # 手动初始化数据源
    CBaoStock.do_init()
    data_src = CBaoStock(code, k_type=KL_TYPE.K_DAY, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)

    is_hold = False
    last_buy_price = None
    for klu in data_src.get_kl_data():  # 逐根获取K线
        chan.trigger_load({KL_TYPE.K_DAY: [klu]})  # 逐根喂给 CChan
        bsp_list = chan.get_latest_bsp()
        if not bsp_list:
            continue
        last_bsp = bsp_list[0]
        if BSP_TYPE.T1 not in last_bsp.type and BSP_TYPE.T1P not in last_bsp.type:
            continue

        cur_lv_chan = chan[0]
        if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
            continue
        if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy and not is_hold:
            last_buy_price = cur_lv_chan[-1][-1].close
            print(f'{cur_lv_chan[-1][-1].time}:buy price = {last_buy_price}')
            is_hold = True
        elif cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy and is_hold:
            sell_price = cur_lv_chan[-1][-1].close
            print(f'{cur_lv_chan[-1][-1].time}:sell price = {sell_price}, profit rate = {(sell_price - last_buy_price) / last_buy_price * 100:.2f}%')
            is_hold = False

    CBaoStock.do_close()