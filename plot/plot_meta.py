from KLine.CKline_List import CKline_List
from KLine.CKLine import KLine
from Bi.CBi import CBi
from Seg.CEigen import CEigen
from Seg.CSeg import CSeg
from common.CEnum import FX_TYPE
from zs.CZS import CZS
from BuySellPoint.CBS_Point import CBS_Point
from stragety.CustomBSP import CCustomBSP, CCloseAction


class Cklc_meta:
    def __init__(self, klc: KLine):
        self.high = klc.high
        self.low = klc.low
        self.begin_idx = klc.lst[0].idx
        self.end_idx = klc.lst[-1].idx
        self.type = klc.fx if klc.fx != FX_TYPE.UNKNOWN else klc.dir

        self.klu_list = []
        for klu in klc.lst:
            self.klu_list.append(klu)


class CBi_meta:
    def __init__(self, bi: CBi):
        self.idx = bi.idx
        self.dir = bi.dir
        self.type = bi.type
        self.begin_x = bi.get_begin_klu().idx
        self.end_x = bi.get_end_klu().idx
        self.begin_y = bi.get_begin_val()
        self.end_y = bi.get_end_val()
        self.id_sure = bi.is_sure


class CSeg_meta:
    def __init__(self, seg: CSeg):
        self.begin_x = seg.start_bi.get_begin_klu().idx
        self.begin_y = seg.start_bi.get_begin_val()
        self.end_x = seg.end_bi.get_end_klu().idx
        self.end_y = seg.end_bi.get_end_val()
        self.is_sure = seg.is_sure


class CEigen_meta:
    def __init__(self, eigen: CEigen, is_up: bool):
        # is_up: 上升笔
        self.begin_x = eigen.lst[0].get_begin_klu().idx
        self.end_x = eigen.lst[-1].get_end_klu().idx
        self.begin_y = eigen.low
        self.end_y = eigen.high
        self.w = self.end_x - self.begin_x
        self.h = self.end_y - self.begin_y
        self.is_up = is_up
        if is_up and eigen.fx == FX_TYPE.BOTTOM or (not is_up and eigen.fx == FX_TYPE.TOP):
            self.fx = eigen.fx
        else:
            self.fx = FX_TYPE.UNKNOWN


class CZS_meta:
    def __init__(self, zs: CZS):
        self.low = zs.low
        self.high = zs.high
        self.begin = zs.begin.idx
        self.end = zs.end.idx
        self.w = self.end - self.begin
        self.h = self.high - self.low
        self.is_sure = zs.is_sure
        self.sub_zs_lst = [CZS_meta(t) for t in zs.sub_zs_lst]


class CBS_Point_meta:
    def __init__(self, bsp: CBS_Point):
        self.is_buy = bsp.is_buy
        self.type = bsp.type2str()

        self.x = bsp.klu.idx
        self.y = bsp.klu.low if self.is_buy else bsp.klu.high

    def desc(self):
        return f'b{self.type}' if self.is_buy else f's{self.type}'


class CCloseActionMeta:
    def __init__(self, action: CCloseAction):
        self.x = action.klu.idx
        self.y = action.price


class CCustomBSP_meta:
    def __init__(self, cbsp: CCustomBSP):
        self.x = cbsp.klu.idx
        self.y = cbsp.klu.low if cbsp.is_buy else cbsp.klu.high
        self.is_buy = cbsp.is_buy
        self.sl_thred = cbsp.sl_thred
        self.bs_type = cbsp.type2str()
        self.profit = cbsp.cal_profit()

        self.close_action = []
        for close_action in cbsp.close_actions:
            self.close_action.append(CCloseActionMeta(close_action))

    def desc(self):
        type_desc = f'b{self.bs_type}!' if self.is_buy else f's{self.bs_type}!'
        profit = f"{self.profit*100:.2f}%" if self.profit else ""
        return f"{type_desc}\n{profit}"


class CChanPlotMeta:
    def __init__(self, kl_list: CKline_List):
        self.data = kl_list

        self.klc_list = []
        for klc in kl_list.lst:
            self.klc_list.append(Cklc_meta(klc))
        self.datetick = [klu.time.to_str() for klu in self.klu_iter()]
        self.klu_len = sum([len(klc.klu_list) for klc in self.klc_list])

        self.bi_list = []
        for bi in kl_list.bi_list:
            self.bi_list.append(CBi_meta(bi))

        self.seg_list = []
        for seg in kl_list.seg_list:
            self.seg_list.append(CSeg_meta(seg))

        self.bi_eigen_lst = []
        if hasattr(kl_list.seg_list, "up_eigen_list"):
            for e in kl_list.seg_list.up_eigen_list:
                self.bi_eigen_lst.append(CEigen_meta(e, True))
            for e in kl_list.seg_list.down_eigen_list:
                self.bi_eigen_lst.append(CEigen_meta(e, False))

        self.zs_lst = []
        for zs in kl_list.zs_list:
            self.zs_lst.append(CZS_meta(zs))

        self.bs_point_lst = []
        for bs_point in kl_list.bs_point_lst:
            self.bs_point_lst.append(CBS_Point_meta(bs_point))

        self.custom_bsp_lst = []
        if kl_list.stragety_cls:
            for cbsp in kl_list.stragety_cls:
                self.custom_bsp_lst.append(CCustomBSP_meta(cbsp))

    def klu_iter(self):
        for klc in self.klc_list:
            for klu in klc.klu_list:
                yield klu

    def sub_last_kseg_start_idx(self, seg_cnt):
        if seg_cnt is None or len(self.data.seg_list) <= seg_cnt:
            return 0
        else:
            return self.data.seg_list[-seg_cnt].getStartKlu().sub_kl_list[0].idx

    def sub_last_kbi_start_idx(self, bi_cnt):
        if bi_cnt is None or len(self.data.bi_list) <= bi_cnt:
            return 0
        else:
            return self.data.bi_list[-bi_cnt].begin_klc.lst[0].sub_kl_list[0].idx

    def sub_range_start_idx(self, x_range):
        for klc in self.data[::-1]:
            for klu in klc[::-1]:
                x_range -= 1
                if x_range == 0:
                    return klu.sub_kl_list[0].idx
        return 0
