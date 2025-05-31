from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock

if __name__ == "__main__":
    """
    一个极其弱智的策略，只交易一类买卖点，底分型形成后就开仓，直到一类卖点顶分型形成后平仓
    只用做展示如何自己实现策略，做回测用~
    相比于strategy_demo.py，本代码演示如何从CChan外部喂K线来触发内部缠论计算
    """
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
        begin_time=begin_time,  # 已经没啥用了这一行
        end_time=end_time,  # 已经没啥用了这一行
        data_src=data_src_type,  # 已经没啥用了这一行
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,  # 已经没啥用了这一行
    )
    CBaoStock.do_init()
    data_src = CBaoStock(code, k_type=KL_TYPE.K_DAY, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)  # 初始化数据源类

    is_hold = False
    last_buy_price = None
    for klu in data_src.get_kl_data():  # 获取单根K线
        chan.trigger_load({KL_TYPE.K_DAY: [klu]})  # 喂给CChan新增k线
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
            print(f'{cur_lv_chan[-1][-1].time}:sell price = {sell_price}, profit rate = {(sell_price-last_buy_price)/last_buy_price*100:.2f}%')
            is_hold = False
    CBaoStock.do_close()
