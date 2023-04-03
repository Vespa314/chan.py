from Bi.BiList import CBiList
from Common.CEnum import SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def is_up_seg(bi, pre_bi):
    return bi._high() > pre_bi._high()


def is_down_seg(bi, pre_bi):
    return bi._low() < pre_bi._low()


class CSegListDef(CSegListComm):
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        super(CSegListDef, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False

    def update(self, bi_lst: CBiList):
        self.do_init()
        self.cal_bi_sure(bi_lst)
        self.collect_left_seg(bi_lst)

    def update_last_end(self, bi_lst, new_endbi_idx: int):
        last_endbi_idx = self[-1].end_bi.idx
        assert new_endbi_idx >= last_endbi_idx + 2
        self[-1].end_bi = bi_lst[new_endbi_idx]
        self.lst[-1].update_bi_list(bi_lst, last_endbi_idx, new_endbi_idx)

    def cal_bi_sure(self, bi_lst):
        peak_bi = None
        if len(bi_lst) == 0:
            return
        for idx, bi in enumerate(bi_lst):
            if idx < 2:
                continue
            if peak_bi and ((bi.is_up() and peak_bi.is_up() and bi._high() >= peak_bi._high()) or (bi.is_down() and peak_bi.is_down() and bi._low() <= peak_bi._low())):
                peak_bi = bi
                continue
            if self.sure_seg_update_end and len(self) and bi.dir == self[-1].dir and ((bi.is_up() and bi._high() >= self[-1].end_bi._high()) or (bi.is_down() and bi._low() <= self[-1].end_bi._low())):
                self.update_last_end(bi_lst, bi.idx)
                peak_bi = None
                continue
            pre_bi = bi_lst[idx-2]
            if (bi.is_up() and is_up_seg(bi, pre_bi)) or \
               (bi.is_down() and is_down_seg(bi, pre_bi)):
                if peak_bi is None:
                    if len(self) == 0 or bi.dir != self[-1].dir:
                        peak_bi = bi
                        continue
                elif peak_bi.dir != bi.dir:
                    if bi.idx - peak_bi.idx <= 2:
                        continue
                    self.add_new_seg(bi_lst, peak_bi.idx)
                    peak_bi = bi
                    continue
        if peak_bi is not None:
            self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False)
