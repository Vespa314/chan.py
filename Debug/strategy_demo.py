# -*- coding: utf-8 -*-
"""
策略演示1 - 基于步进模式的简单一类买卖点策略

Java 开发者注意：
- Python 的 for chan_snapshot in chan.step_load() 是生成器迭代
  step_load() 每次 yield 返回当前状态的 chan 对象
  Java 对比：类似于实现了 Iterator<CChan> 的迭代器
- Python 的 if not bsp_list: 是 Pythonic 的空列表检查
  Java 对比：if (bspList.isEmpty()) 或 if (bspList == null || bspList.isEmpty())
- Python 的 chan_snapshot[0] 调用 __getitem__ 方法
  Java 对比：类似于 chanSnapshot.get(0) 或 chanSnapshot.getKlData(0)
- Python 的 f-string: f'{value:.2f}' 格式化浮点数保留2位小数
  Java 对比：String.format("%.2f", value)

策略说明：
    一个极其简单的演示策略，只交易一类买卖点：
    - 底分型形成后开仓买入
    - 顶分型形成后平仓卖出
    仅用于展示如何使用 chan.py 的步进模式实现交易策略。
"""

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE

if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2021-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": True,  # 打开步进模式！每根K线触发一次
        "divergence_rate": 0.8,
        "min_zs_cnt": 1,
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    is_hold = False        # 是否持仓
    last_buy_price = None  # 上次买入价格
    for chan_snapshot in chan.step_load():  # 每增加一根K线，返回当前静态精算结果
        bsp_list = chan_snapshot.get_latest_bsp()  # 获取最新的买卖点列表
        if not bsp_list:  # 为空则跳过
            continue
        last_bsp = bsp_list[0]  # 最新的一个买卖点

        # 只做一类买卖点（T1/T1P）
        if BSP_TYPE.T1 not in last_bsp.type and BSP_TYPE.T1P not in last_bsp.type:
            continue

        cur_lv_chan = chan_snapshot[0]
        # 确保买卖点与当前K线对齐
        if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
            continue

        # 底分型 + 买点 + 未持仓 → 开仓
        if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy and not is_hold:
            last_buy_price = cur_lv_chan[-1][-1].close  # 开仓价格为最后一根K线close
            print(f'{cur_lv_chan[-1][-1].time}:buy price = {last_buy_price}')
            is_hold = True
        # 顶分型 + 卖点 + 已持仓 → 平仓
        elif cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy and is_hold:
            sell_price = cur_lv_chan[-1][-1].close
            print(f'{cur_lv_chan[-1][-1].time}:sell price = {sell_price}, profit rate = {(sell_price - last_buy_price) / last_buy_price * 100:.2f}%')
            is_hold = False