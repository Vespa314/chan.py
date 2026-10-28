# -*- coding: utf-8 -*-
"""
策略演示4 - 多级别 trigger_load 的时间对齐

Java 开发者注意：
- Python 的 list(data_src_30m.get_kl_data()) 将生成器转换为列表
  Java 对比：stream.collect(Collectors.toList())
- Python 的 enumerate(iterable) 返回 (索引, 值) 的迭代器
  Java 对比：Java 没有直接对应，通常手动维护索引计数器
- Python 的 [klu.time.to_str() for klu in chan[0].klu_iter()] 是列表推导式
  Java 对比：stream().map().collect(Collectors.toList())
- Python 的 _idx 变量名以下划线开头，约定表示"内部使用"的变量
  Java 对比：Java 没有这种命名约定

策略说明：
    演示多级别 trigger_load 时如何解决时间对齐问题。
    核心技巧：
    1. 喂第一根最大级别K线时，一次性把所有次级别K线全部喂入
    2. 之后每次只需要喂一根最大级别K线
    3. 框架内置的 K 线时间对齐能力会自动处理剩余逻辑
    避免了手动进行 K 线对齐的繁琐工作。
"""

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock

if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2023-06-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_30M]

    config = CChanConfig({
        "trigger_step": True,
        "divergence_rate": 0.8,
        "min_zs_cnt": 1,
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,     # 在 trigger_load 模式下这些参数已不再使用
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    CBaoStock.do_init()
    data_src_day = CBaoStock(code, k_type=KL_TYPE.K_DAY, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)
    data_src_30m = CBaoStock(code, k_type=KL_TYPE.K_30M, begin_date=begin_time, end_date=end_time, autype=AUTYPE.QFQ)

    # 一次性获取所有30分钟K线
    kl_30m_all = list(data_src_30m.get_kl_data())

    for _idx, klu in enumerate(data_src_day.get_kl_data()):
        """
        本质是每喂一根日线的时候，这根日线之前的都要喂过。
        提前喂多点不要紧，框架会自动根据日线来截取需要的30M K线。
        30M一口气全部喂完，后续就不用关注时间对齐的问题了。
        """
        if _idx == 0:
            chan.trigger_load({KL_TYPE.K_DAY: [klu], KL_TYPE.K_30M: kl_30m_all})
        else:
            chan.trigger_load({KL_TYPE.K_DAY: [klu]})

        if _idx == 4:  # demo只检查4根日线
            break

        # 检查时间对齐结果
        print("当前所有日线:", [klu.time.to_str() for klu in chan[0].klu_iter()])
        print("当前所有30M K线:", [klu.time.to_str() for klu in chan[1].klu_iter()], "\n")

    CBaoStock.do_close()