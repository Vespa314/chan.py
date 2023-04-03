from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def situation1(cur_bi, next_bi, pre_bi):
    if cur_bi.is_down() and cur_bi._low() > pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < cur_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() < pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > cur_bi._high():
            return True
    return False


def situation2(cur_bi, next_bi, pre_bi):
    if cur_bi.is_down() and cur_bi._low() < pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < pre_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() > pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > pre_bi._high():
            return True
    return False


class CSegListDYH(CSegListComm):
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        super(CSegListDYH, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False

    def update(self, bi_lst: CBiList):
        self.do_init()
        self.cal_bi_sure(bi_lst)
        self.try_update_last_seg(bi_lst)
        if self.left_bi_break(bi_lst):
            self.cal_bi_unsure(bi_lst)
        self.collect_left_seg(bi_lst)

    def cal_bi_sure(self, bi_lst):
        BI_LEN = len(bi_lst)
        next_begin_bi = bi_lst[0]
        for idx, bi in enumerate(bi_lst):
            if idx + 2 >= BI_LEN or idx < 2:
                continue
            if len(self) > 0 and bi.dir != self[-1].end_bi.dir:
                continue
            if bi.is_down() and bi_lst[idx-1]._high() < next_begin_bi._low():
                continue
            if bi.is_up() and bi_lst[idx-1]._low() > next_begin_bi._high():
                continue
            if self.sure_seg_update_end and len(self) and ((bi.is_down() and bi._low() < self[-1].end_bi._low()) or (bi.is_up() and bi._high() > self[-1].end_bi._high())):
                self[-1].end_bi = bi
                if idx != BI_LEN-1:
                    next_begin_bi = bi_lst[idx+1]
                    continue
            if (len(self) == 0 or bi.idx - self[-1].end_bi.idx >= 4) and (situation1(bi, bi_lst[idx + 2], bi_lst[idx - 2]) or situation2(bi, bi_lst[idx + 2], bi_lst[idx - 2])):
                self.add_new_seg(bi_lst, idx-1)
                next_begin_bi = bi

    def cal_bi_unsure(self, bi_lst: CBiList):
        if len(self) == 0:
            return
        last_seg_dir = self[-1].end_bi.dir
        end_bi = None
        peak_value = float("inf") if last_seg_dir == BI_DIR.UP else float("-inf")
        for bi in bi_lst[self[-1].end_bi.idx+3:]:
            if bi.dir == last_seg_dir:
                continue
            cur_value = bi._low() if last_seg_dir == BI_DIR.UP else bi._high()
            if (last_seg_dir == BI_DIR.UP and cur_value < peak_value) or \
               (last_seg_dir == BI_DIR.DOWN and cur_value > peak_value):
                end_bi = bi
                peak_value = cur_value
        if end_bi:
            self.add_new_seg(bi_lst, end_bi.idx, is_sure=False)

    def try_update_last_seg(self, bi_lst: CBiList):
        if len(self) == 0:
            return
        last_bi = self[-1].end_bi
        peak_value = last_bi.get_end_val()
        new_peak_bi = None
        for bi in bi_lst[self[-1].end_bi.idx+1:]:
            if bi.dir != last_bi.dir:
                continue
            if bi.is_down() and bi._low() < peak_value:
                peak_value = bi._low()
                new_peak_bi = bi
            elif bi.is_up() and bi._high() > peak_value:
                peak_value = bi._high()
                new_peak_bi = bi
        if new_peak_bi:
            self[-1].end_bi = new_peak_bi
            self[-1].is_sure = False
