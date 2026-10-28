# -*- coding: utf-8 -*-
"""
定义法线段列表模块 - 使用定义法识别线段

Java 开发者注意：
- Python 的 is_up_seg/is_down_seg 是模块级函数，类似于 Java 的 static 工具方法
- Python 的 bi._high() 和 bi._low() 是"私有"方法（约定以下划线开头）
  Java 对比：Python 没有真正的 private，靠命名约定 _ 表示"请勿直接访问"
- Python 的 assert 是调试断言，生产环境可用 -O 禁用
  Java 对比：Java 的 assert 也可以在运行时禁用
"""

from Bi.BiList import CBiList
from Common.CEnum import SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def is_up_seg(bi, pre_bi):
    """
    判断是否能构成向上线段的条件

    参数:
        bi: 当前笔
        pre_bi: 前前笔（相隔一个笔）

    返回:
        True 如果当前笔的高点高于前前笔的高点

    缠论知识 - 定义法线段：
    定义法线段要求相邻同向笔的高/低点依次抬高/降低。
    向上线段：后一个向上笔的高点 > 前一个向上笔的高点
    向下线段：后一个向下笔的低点 < 前一个向下笔的低点
    """
    return bi._high() > pre_bi._high()


def is_down_seg(bi, pre_bi):
    """
    判断是否能构成向下线段的条件

    参数:
        bi: 当前笔
        pre_bi: 前前笔（相隔一个笔）

    返回:
        True 如果当前笔的低点低于前前笔的低点
    """
    return bi._low() < pre_bi._low()


class CSegListDef(CSegListComm):
    """
    定义法线段列表 - 使用定义法（Peak方法）识别线段

    与特征序列法（Chan）不同，定义法更简单直观：
    同方向的笔，高点依次抬高→向上线段，低点依次降低→向下线段。

    参数:
        seg_config: 线段配置
        lv: 线段级别

    缠论知识 - 定义法线段 vs 特征序列法线段：
    - 定义法：简单直观，但可能产生较多的线段
    - 特征序列法：更严谨，符合缠论原文定义，线段数量更少
    """

    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        super(CSegListDef, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False

    def update(self, bi_lst: CBiList):
        """
        更新线段列表

        参数:
            bi_lst: 笔列表

        处理流程：
        1. 初始化
        2. 计算已确认的线段（cal_bi_sure）
        3. 收集剩余的左侧线段
        """
        self.do_init()
        self.cal_bi_sure(bi_lst)
        self.collect_left_seg(bi_lst)

    def update_last_end(self, bi_lst, new_endbi_idx: int):
        """
        更新最后一个线段的结束点

        参数:
            bi_lst: 笔列表
            new_endbi_idx: 新结束笔的索引

        当发现更极端的峰值时，延伸线段的结束点。
        """
        last_endbi_idx = self[-1].end_bi.idx
        assert new_endbi_idx >= last_endbi_idx + 2
        self[-1].end_bi = bi_lst[new_endbi_idx]
        self.lst[-1].update_bi_list(bi_lst, last_endbi_idx, new_endbi_idx)

    def cal_bi_sure(self, bi_lst):
        """
        计算确定线段

        参数:
            bi_lst: 笔列表

        算法逻辑：
        1. 遍历每根笔（从第3根开始，因为需要前2根作为参考）
        2. 如果当前笔是同向的更大峰值 → 更新峰值参考
        3. 如果同向且峰值更大 → 延伸最后一个线段
        4. 如果满足 is_up_seg/is_down_seg 条件 → 形成新线段

        关键判断：
        - 向上线段：当前向上笔的高点 > 2根前的向上笔的高点
        - 向下线段：当前向下笔的低点 < 2根前的向下笔的低点

        隔2根笔比较的原因是：同向笔之间夹着一根反向笔。
        """
        peak_bi = None
        if len(bi_lst) == 0:
            return

        for idx, bi in enumerate(bi_lst):
            if idx < 2:
                continue  # 前2根笔不参与线段判断

            # 情况1：同向笔且峰值更大 → 更新峰值参考
            if peak_bi and (
                (bi.is_up() and peak_bi.is_up() and bi._high() >= peak_bi._high()) or
                (bi.is_down() and peak_bi.is_down() and bi._low() <= peak_bi._low())
            ):
                peak_bi = bi
                continue

            # 情况2：同向笔且峰值更大 → 延伸线段
            if (
                self.sure_seg_update_end and len(self) and
                bi.dir == self[-1].dir and (
                    (bi.is_up() and bi._high() >= self[-1].end_bi._high()) or
                    (bi.is_down() and bi._low() <= self[-1].end_bi._low())
                )
            ):
                self.update_last_end(bi_lst, bi.idx)
                peak_bi = None
                continue

            # 情况3：满足定义法线段条件
            pre_bi = bi_lst[idx - 2]  # 前前笔（同向比较）
            if (bi.is_up() and is_up_seg(bi, pre_bi)) or \
               (bi.is_down() and is_down_seg(bi, pre_bi)):
                if peak_bi is None:
                    # 还没有峰值参考，且方向与最后一个线段不同
                    if len(self) == 0 or bi.dir != self[-1].dir:
                        peak_bi = bi
                        continue
                elif peak_bi.dir != bi.dir:
                    # 峰值方向与当前笔方向不同 → 形成线段
                    if bi.idx - peak_bi.idx <= 2:
                        continue  # 距离太短，不算
                    self.add_new_seg(bi_lst, peak_bi.idx)
                    peak_bi = bi
                    continue

        # 处理剩余的峰值：标记为未确认的线段
        if peak_bi is not None:
            self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False)