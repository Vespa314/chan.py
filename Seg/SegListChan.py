# -*- coding: utf-8 -*-
"""
特征序列线段列表模块 - 基于特征序列法的线段计算

Java 开发者注意：
- super(CSegListChan, self).__init__(...) 是显式调用父类构造
  Python 3 可用 super().__init__(...)，Java 对比：super(...)
- 函数内 import 是延迟导入，避免循环引用
  Java 对比：Java 不支持延迟导入，import 在编译时解析
"""

from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, SEG_TYPE

from .EigenFX import CEigenFX
from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


class CSegListChan(CSegListComm):
    """
    特征序列法线段列表 - 使用特征序列分形算法计算线段

    这是默认的线段计算算法（推荐使用）。

    算法流程：
    1. do_init: 清理未确认的线段
    2. cal_seg_sure: 遍历笔，用特征序列法找分形，形成确认线段
    3. collect_left_seg: 收集尾部未确认的线段

    缠论知识 - 特征序列线段：
    特征序列法将线段划分问题转化为在特征序列中找分形的问题。
    这本质上是将高维度的"线段"问题降维为低维度的"分形"问题。
    """

    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        super(CSegListChan, self).__init__(seg_config=seg_config, lv=lv)

    def do_init(self):
        """
        初始化：清理末尾未确认的线段

        清理逻辑：
        1. 删除末尾所有 is_sure=False 的线段
           同时清理这些线段中笔的 parent_seg 引用
        2. 如果最后一个确认线段的特征序列分形中
           第三元素包含不确定笔 → 也需要删除该线段重算

        为什么要清理：
        因为新数据到来后，之前不确定的线段可能会被确认或破坏，
        需要重新计算。
        """
        # 删除末尾不确定的线段
        while len(self) and not self.lst[-1].is_sure:
            _seg = self[-1]
            for bi in _seg.bi_list:
                bi.parent_seg = None  # 清空笔的线段引用
            if _seg.pre:
                _seg.pre.next = None
            self.lst.pop()

        # 检查最后一个确认线段的特征序列是否需要重算
        if len(self):
            assert self.lst[-1].eigen_fx and self.lst[-1].eigen_fx.ele[-1]
            if not self.lst[-1].eigen_fx.ele[-1].lst[-1].is_sure:
                # 确定线段的特征序列第三元素包含不确定笔，需要重算
                self.lst.pop()

    def update(self, bi_lst: CBiList):
        """
        更新线段列表（核心入口）

        参数:
            bi_lst: 笔列表

        流程：
        1. do_init: 清理未确认线段
        2. cal_seg_sure: 计算确认线段
        3. collect_left_seg: 收集尾部未确认线段
        """
        self.do_init()
        if len(self) == 0:
            self.cal_seg_sure(bi_lst, begin_idx=0)
        else:
            self.cal_seg_sure(bi_lst, begin_idx=self[-1].end_bi.idx+1)
        self.collect_left_seg(bi_lst)

    def cal_seg_sure(self, bi_lst: CBiList, begin_idx: int):
        """
        使用特征序列法计算确认线段

        参数:
            bi_lst: 笔列表
            begin_idx: 开始计算的笔索引

        核心逻辑：
        1. 创建两个特征序列分形对象：
           - up_eigen: 上升线段的特征序列（找顶分型，收集下降笔）
           - down_eigen: 下降线段的特征序列（找底分型，收集上升笔）
        2. 遍历笔，根据笔的方向添加到对应的特征序列
        3. 先确定第一条线段的方向（特殊处理）
        4. 当某个特征序列找到分形时，处理该分形

        缠论知识 - 两条平行特征序列：
        在遍历过程中，同时维护两条特征序列：
        - 上升线段的特征序列：收集下降笔，找顶分型
        - 下降线段的特征序列：收集上升笔，找底分型

        每条笔只能加入一条特征序列（与当前候选线段方向相反的那条）。
        当某条特征序列找到分形时，就确认了一条线段。
        """
        up_eigen = CEigenFX(BI_DIR.UP, lv=self.lv)  # 上升线段找顶分型，收集下降笔
        down_eigen = CEigenFX(BI_DIR.DOWN, lv=self.lv)  # 下降线段找底分型，收集上升笔
        last_seg_dir = None if len(self) == 0 else self[-1].dir

        for bi in bi_lst[begin_idx:]:
            fx_eigen = None  # 记录找到分形的特征序列

            # 下降笔 → 加入上升线段的特征序列（上升线段中下降笔是特征序列）
            if bi.is_down() and last_seg_dir != BI_DIR.UP:
                if up_eigen.add(bi):
                    fx_eigen = up_eigen
            # 上升笔 → 加入下降线段的特征序列（下降线段中上升笔是特征序列）
            elif bi.is_up() and last_seg_dir != BI_DIR.DOWN:
                if down_eigen.add(bi):
                    fx_eigen = down_eigen

            # 第一条线段的特殊处理：确定方向
            if len(self) == 0:
                # 如果上升特征序列有第二元素且当前是下降笔 → 上升线段失效
                if up_eigen.ele[1] is not None and bi.is_down():
                    last_seg_dir = BI_DIR.DOWN
                    down_eigen.clear()
                # 如果下降特征序列有第二元素且当前是上升笔 → 下降线段失效
                elif down_eigen.ele[1] is not None and bi.is_up():
                    up_eigen.clear()
                    last_seg_dir = BI_DIR.UP
                # 回退逻辑：如果特征序列被清空，恢复方向
                if up_eigen.ele[1] is None and last_seg_dir == BI_DIR.DOWN and bi.dir == BI_DIR.DOWN:
                    last_seg_dir = None
                elif down_eigen.ele[1] is None and last_seg_dir == BI_DIR.UP and bi.dir == BI_DIR.UP:
                    last_seg_dir = None

            if fx_eigen:
                self.treat_fx_eigen(fx_eigen, bi_lst)
                break

    def treat_fx_eigen(self, fx_eigen, bi_lst: CBiList):
        """
        处理找到的特征序列分形

        参数:
            fx_eigen: 找到分形的特征序列
            bi_lst: 笔列表

        逻辑：
        1. 调用 can_be_end 判断线段是否可以结束
        2. 如果可以结束，创建新线段
        3. 如果不行（分形被重置），从分形第二笔重新开始计算

        缠论知识 - 分形确认：
        找到分形后，还需要 can_be_end 来判断是否真的可以结束线段。
        对于第一种情况（无缺口），直接确认。
        对于第二种情况（有缺口），需要等待反向特征序列确认。
        """
        _test = fx_eigen.can_be_end(bi_lst)
        end_bi_idx = fx_eigen.GetPeakBiIdx()

        if _test in [True, None]:  # None表示反向分形找到尾部也没找到
            is_true = _test is not None  # 如果是正常结束
            # 创建新线段
            if not self.add_new_seg(bi_lst, end_bi_idx, is_sure=is_true and fx_eigen.all_bi_is_sure()):
                # 第一条线段的值校验失败，从 end_bi_idx+1 重新开始
                self.cal_seg_sure(bi_lst, end_bi_idx+1)
                return
            self.lst[-1].eigen_fx = fx_eigen  # 保存特征序列分形引用
            if is_true:
                # 线段确认，继续计算后续线段
                self.cal_seg_sure(bi_lst, end_bi_idx + 1)
        else:
            # 分形被重置，从分形第二笔重新开始
            self.cal_seg_sure(bi_lst, fx_eigen.lst[1].idx)