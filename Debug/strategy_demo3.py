# -*- coding: utf-8 -*-
"""
策略演示3 - 小级别K线合成大级别K线

Java 开发者注意：
- Python 的 copy.deepcopy(obj) 是深度拷贝，类似于手动实现 Cloneable + 递归克隆
  Java 对比：没有内置深度拷贝，需要手动实现或使用序列化/反序列化
- Python 的 max(klu.high for klu in klu_15m_lst) 是生成器表达式求最大值
  Java 对比：kluList.stream().mapToDouble(KLine::getHigh).max().orElse(0)
- Python 的 sum(len(klc) for klc in ele_manager) 是生成器表达式求和
  Java 对比：eleManager.stream().mapToInt(klc -> klc.size()).sum()

策略说明：
    演示如何实现小级别K线更新直接刷新 CChan 结果。
    核心思路：
    1. 获取最小级别K线（15分钟）
    2. 将4根15分钟K线合成1根60分钟K线
    3. 每次合成后，用 copy.deepcopy 保存快照
    4. 当15分钟K线不再变化时，确认快照
"""

import copy
from typing import List

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_FIELD, DATA_SRC, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock
from KLine.KLine_Unit import CKLine_Unit


def combine_60m_klu_form_15m(klu_15m_lst: List[CKLine_Unit]) -> CKLine_Unit:
    """
    将4根15分钟K线合成1根60分钟K线

    参数:
        klu_15m_lst: 15分钟K线列表（4根）

    返回:
        合成的60分钟 CKLine_Unit

    合成规则：
    - time: 最后一根15分钟K线的时间
    - open: 第一根15分钟K线的开盘价
    - close: 最后一根15分钟K线的收盘价
    - high: 4根K线中的最高价
    - low: 4根K线中的最低价
    """
    return CKLine_Unit(
        {
            DATA_FIELD.FIELD_TIME: klu_15m_lst[-1].time,
            DATA_FIELD.FIELD_OPEN: klu_15m_lst[0].open,
            DATA_FIELD.FIELD_CLOSE: klu_15m_lst[-1].close,
            DATA_FIELD.FIELD_HIGH: max(klu.high for klu in klu_15m_lst),
            DATA_FIELD.FIELD_LOW: min(klu.low for klu in klu_15m_lst),
        }
    )


if __name__ == "__main__":
    """
    代码不能直接跑，仅用于展示如何实现小级别K线更新直接刷新CChan结果
    """
    code = "sz.000001"
    begin_time = "2023-09-10"
    end_time = None
    data_src_type = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_60M, KL_TYPE.K_15M]

    config = CChanConfig({
        "trigger_step": True,
    })

    # 快照
    chan_snapshot = CChan(
        code=code,
        data_src=data_src_type,
        lv_list=lv_list,
        config=config,
    )

    CBaoStock.do_init()
    data_src = CBaoStock(code, k_type=KL_TYPE.K_15M, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)

    klu_15m_lst_tmp: List[CKLine_Unit] = []  # 存储用于合成当前60M K线的15M K线

    for klu_15m in data_src.get_kl_data():  # 获取单根15分钟K线
        klu_15m_lst_tmp.append(klu_15m)
        klu_60m = combine_60m_klu_form_15m(klu_15m_lst_tmp)  # 合成60分钟K线

        """
        拷贝一份 chan_snapshot
        如果是用序列化方式，这里可以采用 pickle.load()
        """
        chan: CChan = copy.deepcopy(chan_snapshot)
        chan.trigger_load({KL_TYPE.K_60M: [klu_60m], KL_TYPE.K_15M: klu_15m_lst_tmp})

        """
        策略开始：
        这里基于 chan 实现你的策略
        """
        for kl_type, ele_manager in chan.kl_datas.items():
            # 打印当前每一级别分别有多少K线
            print(klu_15m.time, kl_type, sum(len(klc) for klc in ele_manager))
        # 策略结束：

        if len(klu_15m_lst_tmp) == 4:  # 已经完成4根15分钟K线了，说明这个最新的60分钟K线和里面的4根15分钟K线在将来不会再变化
            """
            把当前完整 chan 重新保存成 chan_snapshot
            如果是序列化方式，这里可以采用 pickle.dump()
            """
            chan_snapshot = chan
            klu_15m_lst_tmp = []  # 清空15分钟K线，用于下一个60分钟周期的合成

    CBaoStock.do_close()