from typing import List, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.func_util import revert_bi_dir
from Seg.Seg import CSeg
from Seg.SegListComm import CSegListComm
from ZS.ZSConfig import CZSConfig

from .ZS import CZS


class CZSList:
    def __init__(self, zs_config=CZSConfig()):
        self.zs_lst: List[CZS] = []

        self.config = zs_config
        self.free_item_lst = []

        self.FORCE_CAL_ALL = False  # 控制是否强制计算所有的点，理论上开不开结果一样，效率相差比较多，debug时打开
        self.last_sure_pos = -1  # 上一次计算时sure seg【起始】klu的位置，用起始原因是因为这一次计算可能最后一个线段是刚刚生成的

    def update_last_pos(self, seg_list: CSegListComm):
        self.last_sure_pos = -1
        if self.FORCE_CAL_ALL:
            return
        for seg in seg_list[::-1]:
            if seg.is_sure:
                self.last_sure_pos = seg.end_bi.get_begin_klu().idx
                return

    def seg_need_cal(self, seg: CSeg):
        return seg.end_bi.get_end_klu().idx > self.last_sure_pos

    def add_to_free_lst(self, item, is_sure):
        if len(self.free_item_lst) != 0 and item.idx == self.free_item_lst[-1].idx:
            # 防止笔新高或新低的更新带来bug
            self.free_item_lst = self.free_item_lst[:-1]
        self.free_item_lst.append(item)
        res = self.try_construct_zs(self.free_item_lst, is_sure)  # 可能是一笔中枢
        if res is not None and res.begin_bi.idx > 0:  # 禁止第一笔就是中枢的起点
            self.zs_lst.append(res)
            self.clear_free_lst()
            self.try_combine()

    def clear_free_lst(self):
        self.free_item_lst = []

    def update(self, bi: CBi, is_sure=True):
        if len(self.free_item_lst) == 0 and self.try_add_to_end(bi):
            # zs_combine_mode=peak合并模式下会触发生效，=zs合并一定无效返回
            self.try_combine()  # 新形成的中枢尝试和之前的中枢合并
            return
        self.add_to_free_lst(bi, is_sure)

    def try_add_to_end(self, bi):
        return False if len(self.zs_lst) == 0 else self[-1].try_add_to_end(bi)

    def add_zs_from_bi_range(self, seg_bi_lst: list, seg_dir, seg_is_sure):
        deal_bi_cnt = 0
        for bi in seg_bi_lst:
            if bi.dir == seg_dir:
                continue
            if deal_bi_cnt < 1:  # 防止try_add_to_end执行到上一个线段的中枢里面去
                self.add_to_free_lst(bi, seg_is_sure)
                deal_bi_cnt += 1
            else:
                self.update(bi, seg_is_sure)

    def try_construct_zs(self, lst, is_sure):
        if not self.config.one_bi_zs:
            if len(lst) == 1:
                return None
            else:
                lst = lst[-2:]
        min_high = min(item._high() for item in lst)
        max_low = max(item._low() for item in lst)
        return CZS(lst, is_sure=is_sure) if min_high > max_low else None

    def cal_bi_zs(self, bi_lst: Union[CBiList, CSegListComm], seg_lst: CSegListComm):
        self.zs_lst = [zs for zs in self.zs_lst if zs.end.idx is not None and zs.end.idx <= self.last_sure_pos]

        for seg in seg_lst:
            if not self.seg_need_cal(seg):
                continue
            self.clear_free_lst()
            seg_bi_lst = bi_lst[seg.start_bi.idx:seg.end_bi.idx+1]
            self.add_zs_from_bi_range(seg_bi_lst, seg.dir, seg.is_sure)

        # 处理未生成新线段的部分
        if len(seg_lst):
            self.add_zs_from_bi_range(bi_lst[seg_lst[-1].end_bi.idx+1:], revert_bi_dir(seg_lst[-1].dir), False)

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
        if not self.config.need_combine:
            return
        while len(self.zs_lst) >= 2 and self.zs_lst[-2].combine(self.zs_lst[-1], combine_mode=self.config.zs_combine_mode):
            self.zs_lst = self.zs_lst[:-1]  # 合并后删除最后一个
