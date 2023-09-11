from copy import copy
from typing import List

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock
from KLine.KLine_Unit import CKLine_Unit


def combine_5m_klu_form_1m(klu_1m_lst: List[CKLine_Unit]) -> CKLine_Unit:
    """
    自行实现把一分钟K线合成5分钟K线后返回
    """
    ...


if __name__ == "__main__":
    """
    代码不能直接跑，仅用于展示如何实现小级别K线更新直接刷新CChan结果
    """
    code = "sz.000001"
    begin_time = "2021-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_5M, KL_TYPE.K_1M]

    config = CChanConfig({
        "triger_step": True,
    })

    # 快照
    chan_snapshot = CChan(
        code=code,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
    )
    CBaoStock.do_init()
    data_src = CBaoStock(code, k_type=KL_TYPE.K_1M, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)  # 获取最小级别

    klu_1m_lst_tmp: List[CKLine_Unit] = []  # 存储用于合成当前5M K线的1M k线

    for klu_1m in data_src.get_kl_data():  # 获取单根1分钟K线
        klu_1m_lst_tmp.append(klu_1m)
        klu_5m = combine_5m_klu_form_1m(klu_1m_lst_tmp)  # 合成5分钟K线

        """
        拷贝一份chan_snapshot
        如果是用序列化方式，这里可以采用pickle.load()
        """
        chan: CChan = copy.deepcopy(chan_snapshot)
        chan.trigger_load({KL_TYPE.K_5M: [klu_5m], KL_TYPE.K_1M: klu_1m_lst_tmp})

        """
        这里基于chan实现你的策略
        """

        if len(klu_1m_lst_tmp) == 5:  # 已经完成5根1分钟K线了，说明这个最新的5分钟K线和里面的5根1分钟K线在将来不会再变化
            """
            把当前完整chan重新保存成chan_snapshot
            如果是序列化方式，这里可以采用pickle.dump()
            """
            chan_snapshot = chan
            klu_1m_lst_tmp = []  # 清空1分钟K线，用于下一个五分钟周期的合成

    CBaoStock.do_close()
