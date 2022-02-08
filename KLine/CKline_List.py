from .CKline_Unit import KLine_Unit
from .CKLine import KLine
from common.CEnum import KLINE_DIR
from dataSrc.CommonStockAPI import TRADE_INFO_LST
from Bi.CBiList import CBi_List
from ChanConfig import CChanConfig
from Seg.CSegListChan import CSegListChan
from Seg.CSegConfig import CSeg_Config
from Seg.CSegListDYH import CSeg_List_DYH
from Seg.CSegListDef import CSegListDef
from zs.CZSList import CZS_List
from BuySellPoint.CBSPointList import CBSPointList
from Math.OutlinerDetection import CNormOutlinerDetection


def get_seglist_instance(seg_config: CSeg_Config):
    if seg_config.seg_algo == "chan":
        return CSegListChan(seg_config)
    elif seg_config.seg_algo == "1+1":
        return CSeg_List_DYH(seg_config)
    elif seg_config.seg_algo == "break":
        return CSegListDef(seg_config)
    else:
        raise Exception(f"unsupport seg algoright:{seg_config.seg_algo}")


class CKline_List:
    def __init__(self, kl_type, conf: CChanConfig):
        self.kl_type = kl_type
        self.config = conf
        self.lst = []  # K线列表，可递归  元素KLine类型
        self.bi_list = CBi_List(bi_conf=conf.bi_conf)
        self.seg_list = get_seglist_instance(seg_config=conf.seg_conf)
        self.segseg_list = get_seglist_instance(seg_config=conf.seg_conf)

        self.zs_list = CZS_List(zs_config=conf.zs_conf)
        self.segzs_list = CZS_List(zs_config=conf.zs_conf)

        self.bs_point_lst = CBSPointList(bs_point_config=conf.bs_point_conf)

        self.metric_model_lst = conf.GetMetricModel()

        od_conf = {"win_width": conf.od_win_width,
                   "mean_thred": conf.od_mean_thred,
                   "max_zero_cnt": conf.od_max_zero_cnt,
                   "skip_zero": conf.od_skip_zero,
                   }
        self.tradeinfo_outlinerdetection_dict = {
            metric_name: CNormOutlinerDetection(metric_name, **od_conf) for metric_name in TRADE_INFO_LST
        }

        if conf.stragety_cls:
            self.stragety_cls = conf.stragety_cls(conf)
        else:
            self.stragety_cls = None

    def __getitem__(self, n):
        if isinstance(n, int):
            return self.lst[n]
        elif isinstance(n, slice):
            return self.lst[n.start:n.stop:n.step]

    def __len__(self):
        return len(self.lst)

    def cal_seg_and_zs(self):
        cal_seg(self.bi_list, self.seg_list)
        self.zs_list.cal_bi_zs(self.bi_list, self.seg_list)
        cal_zs_in_seg(self.bi_list, self.seg_list, self.zs_list)  # 计算seg的zs_lst，以及中枢的bi_in, bi_out

        cal_seg(self.seg_list, self.segseg_list)
        self.segzs_list.cal_bi_zs(self.seg_list, self.segseg_list)
        cal_zs_in_seg(self.seg_list, self.segseg_list, self.segzs_list)  # 计算segseg的zs_lst，以及中枢的bi_in, bi_out

        self.cal_klc_in_bi()  # 计算每一笔里面的 klc列表
        self.figure_bs_point()

    def figure_bs_point(self):
        self.bs_point_lst.cal(self.bi_list, self.seg_list)

    def add_single_klu(self, klu: KLine_Unit):
        klu.set_metric(self.metric_model_lst)
        klu.update_outliner(self.tradeinfo_outlinerdetection_dict)
        if len(self.lst) == 0:
            self.lst.append(KLine(klu, idx=0))
        else:
            _dir = self.lst[-1].try_add(klu)
            if _dir != KLINE_DIR.COMBINE:  # 不需要合并K线
                self.lst.append(KLine(klu, idx=len(self.lst), _dir=_dir))
                if len(self.lst) >= 3:
                    self.lst[-2].update_fx(self.lst[-3], self.lst[-1])
                if self.bi_list.update_bi(self.lst[-2], self.lst[-1]):
                    if self.config.triger_step or (self.stragety_cls is not None and self.stragety_cls.conf.only_judge_last is False):  # 回放模式
                        self.cal_seg_and_zs()
            else:
                if self.bi_list.try_add_virtual_bi(self.lst[-1]):
                    if self.config.triger_step or (self.stragety_cls is not None and self.stragety_cls.conf.only_judge_last is False):  # 回放模式
                        self.cal_seg_and_zs()

    def klu_iter(self):
        for klc in self.lst:
            for klu in klc.lst:
                yield klu

    def cal_klc_in_bi(self):
        for bi in self.bi_list:
            bi.klc_lst = self[bi.begin_klc.idx:bi.end_klc.idx+1]

    def toJson(self):
        res = {
            "bi_list": self.bi_list.toJson(),
            "seg_list": self.seg_list.toJson(),
            "zs_list": self.zs_list.toJson(),
            "bsp_list": self.bs_point_lst.toJson(),
        }
        if self.stragety_cls:
            res.update({"stragety": self.stragety_cls.toJson()})
        return res

    def cal_cbsp_summary(self):
        if self.stragety_cls:
            self.stragety_cls.summary(self)


def cal_seg(bi_list, seg_list):
    seg_list.update(bi_list)
    # 计算每一笔属于哪个线段
    bi_seg_idx_dict = {}
    for seg_idx, seg in enumerate(seg_list):
        for i in range(seg.start_bi.idx, seg.end_bi.idx+1):
            bi_seg_idx_dict[i] = seg_idx
    for bi in bi_list:
        bi.seg_idx = bi_seg_idx_dict.get(bi.idx, len(seg_list))  # 找不到的应该都是最后一个线段的


def cal_zs_in_seg(bi_list, seg_list, zs_list):
    for seg in seg_list:
        seg.clear_zs_lst()
        for zs in zs_list:
            if zs.is_inside(seg):
                seg.add_zs(zs)
            assert zs.begin_bi.idx > 0
            zs.bi_in = bi_list[zs.begin_bi.idx-1]
            if zs.end_bi.idx+1 < len(bi_list):
                zs.bi_out = bi_list[zs.end_bi.idx+1]
            zs.bi_lst = []
            for bi in bi_list[zs.begin_bi.idx:zs.end_bi.idx+1]:
                zs.bi_lst.append(bi)
