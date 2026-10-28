# -*- coding: utf-8 -*-
"""
都业华法线段列表模块 - 使用都业华线段算法识别线段

Java 开发者注意：
- Python 的模块级函数 situation1/situation2 类似于 Java 的 static 工具方法
- Python 的 if 条件支持多行换行（用 \ 续行），Java 同样支持
- Python 的 float("inf") 正无穷，float("-inf") 负无穷
  Java 对比：Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY
- Python 列表切片 bi_lst[idx+3:] 取从 idx+3 到末尾的所有元素
  Java 对比：biList.subList(idx+3, biList.size())
"""

from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def situation1(cur_bi, next_bi, pre_bi):
    """
    都业华法线段判断 - 情况1：当前笔被包含

    参数:
        cur_bi: 当前笔
        next_bi: 后一笔
        pre_bi: 前一笔

    返回:
        True 如果满足情况1

    情况1 描述：
    - 向下线段：当前笔的低点 > 前一笔的低点（未创新低），
      且下一笔的高点 < 当前笔的高点，下一笔的低点 < 当前笔的低点
    - 向上线段：当前笔的高点 < 前一笔的高点（未创新高），
      且下一笔的低点 > 当前笔的低点，下一笔的高点 > 当前笔的高点

    缠论知识 - 都业华法：
    都业华法是另一种线段划分方法，由都业华（缠论研究者）提出。
    相比特征序列法更直观，通过相邻笔的关系判断线段端点。
    都业华法主要关注"笔的包含关系"和"笔的突破关系"。
    """
    if cur_bi.is_down() and cur_bi._low() > pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < cur_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() < pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > cur_bi._high():
            return True
    return False


def situation2(cur_bi, next_bi, pre_bi):
    """
    都业华法线段判断 - 情况2：当前笔突破

    参数:
        cur_bi: 当前笔
        next_bi: 后一笔
        pre_bi: 前一笔

    返回:
        True 如果满足情况2

    情况2 描述：
    - 向下线段：当前笔的低点 < 前一笔的低点（创新低），
      且下一笔的高点 < 当前笔的高点，下一笔的低点 < 前一笔的低点
    - 向上线段：当前笔的高点 > 前一笔的高点（创新高），
      且下一笔的低点 > 当前笔的低点，下一笔的高点 > 前一笔的高点

    情况2 与情况1 的关键区别：
    - 情况1：当前笔未创新高/新低（被包含）
    - 情况2：当前笔创新高/新低（突破），但随后被反向笔打破
    """
    if cur_bi.is_down() and cur_bi._low() < pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < pre_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() > pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > pre_bi._high():
            return True
    return False


class CSegListDYH(CSegListComm):
    """
    都业华法线段列表 - 使用都业华算法识别线段

    都业华法的特点：
    1. 通过笔的包含/突破关系判断线段端点
    2. 支持线段端点更新（延伸）
    3. 分为确认线段（sure）和未确认线段（unsure）两个阶段

    参数:
        seg_config: 线段配置
        lv: 线段级别

    缠论知识 - 三种线段算法对比：
    - 特征序列法（Chan）：最严谨，线段数量最少
    - 定义法（Def）：最简单，线段数量最多
    - 都业华法（DYH）：介于两者之间，注重笔的包含和突破关系
    """

    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        super(CSegListDYH, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False

    def update(self, bi_lst: CBiList):
        """
        更新线段列表

        参数:
            bi_lst: 笔列表

        处理流程：
        1. 初始化
        2. 计算确认的线段（cal_bi_sure）
        3. 尝试更新最后一个线段（try_update_last_seg）
        4. 如果左侧笔已突破 → 计算未确认的线段（cal_bi_unsure）
        5. 收集剩余的左侧线段
        """
        self.do_init()
        self.cal_bi_sure(bi_lst)
        self.try_update_last_seg(bi_lst)
        if self.left_bi_break(bi_lst):
            self.cal_bi_unsure(bi_lst)
        self.collect_left_seg(bi_lst)

    def cal_bi_sure(self, bi_lst):
        """
        计算确定的线段

        参数:
            bi_lst: 笔列表

        算法逻辑：
        遍历每根笔，判断是否满足以下条件之一：
        1. situation1（包含）：当前笔未被突破，但形成包含关系
        2. situation2（突破）：当前笔突破前高/前低，但被反向笔打破

        额外条件：
        - 需要至少 4 根笔的间隔（idx - last_end_bi.idx >= 4）
        - 当前笔方向必须与最后一个线段方向相同
        - 前一笔不能被反向笔突破
        """
        BI_LEN = len(bi_lst)
        next_begin_bi = bi_lst[0]

        for idx, bi in enumerate(bi_lst):
            if idx + 2 >= BI_LEN or idx < 2:
                continue  # 前后各需要2根笔作为参考

            # 方向必须与最后一个线段方向相同
            if len(self) > 0 and bi.dir != self[-1].end_bi.dir:
                continue

            # 前一笔不能被反向笔突破
            if bi.is_down() and bi_lst[idx - 1]._high() < next_begin_bi._low():
                continue
            if bi.is_up() and bi_lst[idx - 1]._low() > next_begin_bi._high():
                continue

            # 同向延伸：峰值更大 → 更新线段端点
            if self.sure_seg_update_end and len(self) and (
                (bi.is_down() and bi._low() < self[-1].end_bi._low()) or
                (bi.is_up() and bi._high() > self[-1].end_bi._high())
            ):
                self[-1].end_bi = bi
                if idx != BI_LEN - 1:
                    next_begin_bi = bi_lst[idx + 1]
                    continue

            # 至少间隔4根笔，且满足都业华法的两种情况之一
            if (
                len(self) == 0 or bi.idx - self[-1].end_bi.idx >= 4
            ) and (
                situation1(bi, bi_lst[idx + 2], bi_lst[idx - 2]) or
                situation2(bi, bi_lst[idx + 2], bi_lst[idx - 2])
            ):
                self.add_new_seg(bi_lst, idx - 1)
                next_begin_bi = bi

    def cal_bi_unsure(self, bi_lst: CBiList):
        """
        计算未确认的线段

        参数:
            bi_lst: 笔列表

        当左侧笔已突破时，在最后一个线段之后寻找可能的新线段端点。
        找到反向笔中最极端的峰值作为候选端点。
        """
        if len(self) == 0:
            return

        last_seg_dir = self[-1].end_bi.dir
        end_bi = None
        # 初始峰值：与线段方向相反（找最极端的反向点）
        peak_value = float("inf") if last_seg_dir == BI_DIR.UP else float("-inf")

        for bi in bi_lst[self[-1].end_bi.idx + 3:]:
            if bi.dir == last_seg_dir:
                continue  # 同向笔不参与
            # 找最极端的反向峰值
            cur_value = bi._low() if last_seg_dir == BI_DIR.UP else bi._high()
            if (last_seg_dir == BI_DIR.UP and cur_value < peak_value) or \
               (last_seg_dir == BI_DIR.DOWN and cur_value > peak_value):
                end_bi = bi
                peak_value = cur_value

        if end_bi:
            self.add_new_seg(bi_lst, end_bi.idx, is_sure=False)

    def try_update_last_seg(self, bi_lst: CBiList):
        """
        尝试更新最后一个线段的端点

        参数:
            bi_lst: 笔列表

        如果最后一个线段之后出现了同向的更极端的峰值，
        则更新线段端点（线段延伸）。
        更新后线段变为未确认状态（is_sure=False）。
        """
        if len(self) == 0:
            return

        last_bi = self[-1].end_bi
        peak_value = last_bi.get_end_val()
        new_peak_bi = None

        for bi in bi_lst[self[-1].end_bi.idx + 1:]:
            if bi.dir != last_bi.dir:
                continue  # 非同向笔跳过
            if bi.is_down() and bi._low() < peak_value:
                peak_value = bi._low()
                new_peak_bi = bi
            elif bi.is_up() and bi._high() > peak_value:
                peak_value = bi._high()
                new_peak_bi = bi

        if new_peak_bi:
            self[-1].end_bi = new_peak_bi
            self[-1].is_sure = False  # 更新后变为未确认