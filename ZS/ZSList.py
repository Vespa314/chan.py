# -*- coding: utf-8 -*-
"""
中枢列表模块 - 管理中枢的创建、合并和更新

Java 开发者注意：
- yield from 是生成器委托，类似于 Java 的 Stream.flatMap()
- Python 的列表切片 lst[-2:] 取最后两个元素，类似于 Java 的 subList
- Python 的 pop() 删除并返回最后一个元素，类似于 Java 的 remove(list.size()-1)
"""

from typing import List, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.func_util import revert_bi_dir
from Seg.Seg import CSeg
from Seg.SegListComm import CSegListComm
from ZS.ZSConfig import CZSConfig

from .ZS import CZS


class CZSList:
    """
    中枢列表 - 管理某一级别下的所有中枢

    中枢的创建过程：
    1. 遍历线段中的笔，收集反向笔到 free_item_lst
    2. 当 free_item_lst 中有足够多的笔时，尝试构建中枢
    3. 新中枢形成后，尝试与已有中枢合并

    属性说明：
    - zs_lst: 中枢列表
    - config: 中枢配置
    - free_item_lst: 待构建中枢的笔缓存
    - last_sure_pos: 最后一个确认中枢的位置
    - last_seg_idx: 最后一个确认中枢的线段索引
    """

    def __init__(self, zs_config=CZSConfig()):
        self.zs_lst: List[CZS] = []
        self.config = zs_config
        self.free_item_lst = []  # 待构建中枢的笔缓存
        self.last_sure_pos = -1
        self.last_seg_idx = 0

    def update_last_pos(self, seg_list: CSegListComm):
        """
        更新最后一个确认中枢的位置

        从后往前找最后一个确认的线段，记录其起始位置。
        用于增量更新时判断哪些中枢需要重算。
        """
        self.last_sure_pos = -1
        self.last_seg_idx = 0
        _seg_idx = len(seg_list) - 1
        while _seg_idx >= 0:
            seg = seg_list[_seg_idx]
            if seg.is_sure:
                self.last_sure_pos = seg.start_bi.idx
                self.last_seg_idx = seg.idx
                return
            _seg_idx -= 1

    def seg_need_cal(self, seg: CSeg):
        """判断线段是否需要重新计算中枢"""
        return seg.start_bi.idx >= self.last_sure_pos

    def add_to_free_lst(self, item, is_sure, zs_algo):
        """
        将一笔添加到待构建中枢的缓存中

        参数:
            item: 待添加的笔
            is_sure: 是否确认
            zs_algo: 中枢算法

        逻辑：
        1. 防止笔新高/新低更新带来的重复bug
        2. 尝试构建中枢（try_construct_zs）
        3. 如果构建成功，加入中枢列表并尝试合并
        """
        if len(self.free_item_lst) != 0 and item.idx == self.free_item_lst[-1].idx:
            # 防止笔新高或新低的更新带来bug（同一笔重复添加）
            self.free_item_lst = self.free_item_lst[:-1]
        self.free_item_lst.append(item)
        res = self.try_construct_zs(self.free_item_lst, is_sure, zs_algo)
        if res is not None and res.begin_bi.idx > 0:  # 禁止第一笔就是中枢的起点
            self.zs_lst.append(res)
            self.clear_free_lst()
            self.try_combine()  # 尝试与已有中枢合并

    def clear_free_lst(self):
        """清空待构建中枢的缓存"""
        self.free_item_lst = []

    def update(self, bi: CBi, is_sure=True):
        """
        更新中枢列表（添加一笔）

        参数:
            bi: 新笔
            is_sure: 是否确认

        逻辑：
        1. 如果 free_item_lst 为空，先尝试添加到最后一个中枢的末尾
        2. 如果添加失败，加入 free_item_lst 等待构建新中枢
        """
        if len(self.free_item_lst) == 0 and self.try_add_to_end(bi):
            self.try_combine()  # 新形成的中枢尝试和之前的中枢合并
            return
        self.add_to_free_lst(bi, is_sure, "normal")

    def try_add_to_end(self, bi):
        """
        尝试将一笔添加到最后一个中枢的末尾

        返回:
            True 如果添加成功
        """
        return False if len(self.zs_lst) == 0 else self[-1].try_add_to_end(bi)

    def add_zs_from_bi_range(self, seg_bi_lst: list, seg_dir, seg_is_sure):
        """
        从一个区间内的笔构建中枢

        参数:
            seg_bi_lst: 线段内的笔列表
            seg_dir: 线段方向
            seg_is_sure: 线段是否确认

        逻辑：
        遍历线段中的笔，跳过与线段同向的笔（中枢由反向笔构成）。
        第一笔跳过 try_add_to_end 防止加入到上一个线段的中枢。
        """
        deal_bi_cnt = 0
        for bi in seg_bi_lst:
            if bi.dir == seg_dir:
                continue  # 跳过与线段同向的笔
            if deal_bi_cnt < 1:
                # 第一笔不执行 try_add_to_end，防止加到上一个线段的中枢
                self.add_to_free_lst(bi, seg_is_sure, "normal")
                deal_bi_cnt += 1
            else:
                self.update(bi, seg_is_sure)

    def try_construct_zs(self, lst, is_sure, zs_algo):
        """
        尝试从笔列表中构建中枢

        参数:
            lst: 笔列表
            is_sure: 是否确认
            zs_algo: 中枢算法

        返回:
            CZS 对象如果构建成功，None 如果失败

        构建条件：
        - normal 模式：至少需要2笔（构成中枢区间的高点和低点）
        - over_seg 模式：至少需要3笔

        中枢区间 = [max(各笔的_low), min(各笔的_high)]
        如果 min_high > max_low，则形成中枢（有重叠区间）。
        """
        if zs_algo == "normal":
            if not self.config.one_bi_zs:
                if len(lst) == 1:
                    return None
                else:
                    lst = lst[-2:]  # 只取最后2笔
        elif zs_algo == "over_seg":
            if len(lst) < 3:
                return None
            lst = lst[-3:]
            if lst[0].dir == lst[0].parent_seg.dir:
                lst = lst[1:]
                return None
        min_high = min(item._high() for item in lst)
        max_low = max(item._low() for item in lst)
        return CZS(lst, is_sure=is_sure) if min_high > max_low else None

    def cal_bi_zs(self, bi_lst: Union[CBiList, CSegListComm], seg_lst: CSegListComm):
        """
        计算所有笔中枢（核心入口方法）

        参数:
            bi_lst: 笔列表（或线段列表）
            seg_lst: 线段列表

        三种算法：
        1. normal: 按线段遍历，每段内找中枢
        2. over_seg: 跨线段找中枢（不按线段分割）
        3. auto: 自动选择（确认线段用 normal，未确认线段用 over_seg）
        """
        # 清理需要重算的中枢
        while self.zs_lst and self.zs_lst[-1].begin_bi.idx >= self.last_sure_pos:
            self.zs_lst.pop()

        if self.config.zs_algo == "normal":
            # 标准算法：按线段遍历
            for seg in seg_lst[self.last_seg_idx:]:
                if not self.seg_need_cal(seg):
                    continue
                self.clear_free_lst()
                seg_bi_lst = bi_lst[seg.start_bi.idx:seg.end_bi.idx+1]
                self.add_zs_from_bi_range(seg_bi_lst, seg.dir, seg.is_sure)

            # 处理未生成新线段的部分
            if len(seg_lst):
                self.clear_free_lst()
                self.add_zs_from_bi_range(bi_lst[seg_lst[-1].end_bi.idx+1:], revert_bi_dir(seg_lst[-1].dir), False)

        elif self.config.zs_algo == "over_seg":
            # 跨线段算法
            assert self.config.one_bi_zs is False
            self.clear_free_lst()
            begin_bi_idx = self.zs_lst[-1].end_bi.idx+1 if self.zs_lst else 0
            for bi in bi_lst[begin_bi_idx:]:
                self.update_overseg_zs(bi)

        elif self.config.zs_algo == "auto":
            # 自动选择算法
            sure_seg_appear = False
            exist_sure_seg = seg_lst.exist_sure_seg()
            for seg in seg_lst[self.last_seg_idx:]:
                if seg.is_sure:
                    sure_seg_appear = True
                if not self.seg_need_cal(seg):
                    continue
                if seg.is_sure or (not sure_seg_appear and exist_sure_seg):
                    self.clear_free_lst()
                    self.add_zs_from_bi_range(bi_lst[seg.start_bi.idx:seg.end_bi.idx+1], seg.dir, seg.is_sure)
                else:
                    # 未确认线段用 over_seg 算法
                    self.clear_free_lst()
                    for bi in bi_lst[seg.start_bi.idx:]:
                        self.update_overseg_zs(bi)
                    break
        else:
            raise Exception(f"unknown zs_algo {self.config.zs_algo}")

        self.update_last_pos(seg_lst)

    def update_overseg_zs(self, bi: CBi | CSeg):
        """
        跨线段模式的中枢更新

        参数:
            bi: 笔或线段

        比 normal 模式更宽松的中枢构建方式：
        不严格按线段分割，允许跨线段形成中枢。
        """
        if len(self.zs_lst) and len(self.free_item_lst) == 0:
            if bi.next is None:
                return
            if bi.idx - self.zs_lst[-1].end_bi.idx <= 1 and self.zs_lst[-1].in_range(bi.next) and self.zs_lst[-1].try_add_to_end(bi):
                return
        if len(self.zs_lst) and len(self.free_item_lst) == 0 and self.zs_lst[-1].in_range(bi) and bi.idx - self.zs_lst[-1].end_bi.idx <= 1:
            return
        self.add_to_free_lst(bi, bi.is_sure, zs_algo="over_seg")

    def __iter__(self):
        yield from self.zs_lst

    def __len__(self):
        return len(self.zs_lst)

    @overload
    def __getitem__(self, index: int) -> CZS: ...

    @overload
    def __getitem__(self, index: slice) -> List[CZS]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CZS], CZS]:
        return self.zs_lst[index]

    def try_combine(self):
        """
        尝试合并相邻的中枢

        合并逻辑：
        从后往前检查，如果最后两个中枢可以合并，
        将倒数第二个扩展（合并最后一个），然后删除最后一个。
        重复此过程直到不能合并为止。

        合并条件：
        - need_combine=True 且相同线段内的中枢区间有重叠
        """
        if not self.config.need_combine:
            return
        while len(self.zs_lst) >= 2 and self.zs_lst[-2].combine(self.zs_lst[-1], combine_mode=self.config.zs_combine_mode):
            self.zs_lst = self.zs_lst[:-1]  # 合并后删除最后一个