# -*- coding: utf-8 -*-
"""
笔的简单用例测试 - 构造一段锯齿走势的日线数据，验证笔的识别

运行方式（在项目根目录）：
    .venv/bin/python Debug/bi_test.py

本测试不依赖任何外部数据源（无需联网），直接在内存中构造 K 线，
走 CKLine_List.add_single_klu 的完整笔计算流程，然后打印并校验结果。

走势设计（close 序列，形成明确的顶底分型）：
    上涨 11→15，下跌 15→9，上涨 9→14，下跌 14→8，上涨 8→13
    预期形成 3 笔确认笔：下、上、下（方向交替）
"""

import datetime
import os
import sys

# 将项目根目录加入 sys.path，使脚本可从任意目录直接运行（无需 PYTHONPATH）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChanConfig import CChanConfig
from Common.CEnum import BI_DIR, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_List import CKLine_List
from KLine.KLine_Unit import CKLine_Unit


def make_klu(year, month, day, o, h, l, c):
    """构造一根日线 CKLine_Unit（时间 + OHLC）"""
    klu = CKLine_Unit({
        DATA_FIELD.FIELD_TIME: CTime(year, month, day, 0, 0),
        DATA_FIELD.FIELD_OPEN: float(o),
        DATA_FIELD.FIELD_HIGH: float(h),
        DATA_FIELD.FIELD_LOW: float(l),
        DATA_FIELD.FIELD_CLOSE: float(c),
    })
    klu.kl_type = KL_TYPE.K_DAY
    return klu


def build_sawtooth_close():
    """构造锯齿走势的 close 序列，确保形成多个顶底分型"""
    prices = []
    prices += [11, 12, 13, 14, 15]        # 上涨：底→顶
    prices += [14, 13, 12, 11, 10, 9]     # 下跌：顶→底
    prices += [10, 11, 12, 13, 14]        # 上涨：底→顶
    prices += [13, 12, 11, 10, 9, 8]      # 下跌：顶→底
    prices += [9, 10, 11, 12, 13]         # 上涨：底→顶（尾部未完成）
    return prices


def main():
    config = CChanConfig({"bi_strict": True})
    kl_list = CKLine_List(KL_TYPE.K_DAY, conf=config)

    prices = build_sawtooth_close()
    base = datetime.date(2024, 1, 1)

    prev_close = prices[0]
    for i, c in enumerate(prices):
        d = base + datetime.timedelta(days=i)
        o = prev_close                       # 开盘 = 前收
        h = max(o, c) + 0.3                  # 加影线，保证 low<=o,c<=high
        l = min(o, c) - 0.3
        klu = make_klu(d.year, d.month, d.day, o, h, l, c)
        klu.set_idx(i)                       # 手动设置原始K线索引（正常由 CChan 设置）
        kl_list.add_single_klu(klu)
        prev_close = c

    # 读结果：bi_list 是 CBiList，可直接 for / len / 下标
    bi_list = kl_list.bi_list
    print(f"合并K线数 = {len(kl_list.lst)}")
    print(f"识别出 {len(bi_list)} 笔\n")

    for bi in bi_list:
        direction = "↑ 上升笔" if bi.dir == BI_DIR.UP else "↓ 下降笔"
        state = "确认" if bi.is_sure else "虚拟"
        print(f"笔#{bi.idx} {direction} [{state}]")
        print(f"    起始: {bi.begin_klc.time_begin}~{bi.begin_klc.time_end}  值={bi.get_begin_val():.2f}")
        print(f"    结束: {bi.end_klc.time_begin}~{bi.end_klc.time_end}  值={bi.get_end_val():.2f}")
        print(f"    原始K线数={bi.get_klu_cnt()}  振幅={bi.amp():.2f}")
        print()

    # ===== 简单断言 =====
    assert len(bi_list) >= 2, f"笔数量过少：{len(bi_list)}"
    for a, b in zip(bi_list, bi_list[1:]):
        assert a.dir != b.dir, "相邻笔方向应交替（顶底分型交替）"
    for bi in bi_list:
        if bi.is_up():
            assert bi.get_begin_val() < bi.get_end_val(), "上升笔起点应低于终点"
        else:
            assert bi.get_begin_val() > bi.get_end_val(), "下降笔起点应高于终点"

    print(f"✅ 测试通过：识别 {len(bi_list)} 笔，方向正确交替，起止值与方向一致")


if __name__ == "__main__":
    main()
