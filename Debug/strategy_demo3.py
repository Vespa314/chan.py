import copy
from typing import List

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_FIELD, DATA_SRC, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock
from KLine.KLine_Unit import CKLine_Unit


def combine_60m_klu_form_15m(klu_15m_lst: List[CKLine_Unit]) -> CKLine_Unit:
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
    data_src = CBaoStock(code, k_type=KL_TYPE.K_15M, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)  # 获取最小级别

    klu_15m_lst_tmp: List[CKLine_Unit] = []  # 存储用于合成当前60M K线的15M k线

    for klu_15m in data_src.get_kl_data():  # 获取单根15分钟K线
        klu_15m_lst_tmp.append(klu_15m)
        klu_60m = combine_60m_klu_form_15m(klu_15m_lst_tmp)  # 合成60分钟K线

        """
        拷贝一份chan_snapshot
        如果是用序列化方式，这里可以采用pickle.load()
        """
        chan: CChan = copy.deepcopy(chan_snapshot)
        chan.trigger_load({KL_TYPE.K_60M: [klu_60m], KL_TYPE.K_15M: klu_15m_lst_tmp})

        """
        策略开始：
        这里基于chan实现你的策略
        """
        for kl_type, ele_manager in chan.kl_datas.items():
            # 打印当前每一级别分别有多少K线
            print(klu_15m.time, kl_type, sum(len(klc) for klc in ele_manager))
        # 策略结束：

        if len(klu_15m_lst_tmp) == 4:  # 已经完成4根15分钟K线了，说明这个最新的60分钟K线和里面的4根15分钟K线在将来不会再变化
            """
            把当前完整chan重新保存成chan_snapshot
            如果是序列化方式，这里可以采用pickle.dump()
            """
            chan_snapshot = chan
            klu_15m_lst_tmp = []  # 清空1分钟K线，用于下一个五分钟周期的合成

    CBaoStock.do_close()
