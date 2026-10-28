# -*- coding: utf-8 -*-
"""
买卖点列表模块 - 管理买卖点的计算、存储和检索

Java 开发者注意：
- Generic[LINE_TYPE, LINE_LIST_TYPE] 是 Python 多泛型参数，类似于 Java 的 <T, U>
- yield from 是生成器委托，类似于 Java 的 Stream.flatMap()
- Python 的 sorted(list, key=lambda) 类似于 Java 的 stream.sorted(Comparator.comparing())
- Python 的 := 海象运算符在表达式中赋值，Java 没有直接对应
- Python 的 Optional[T] 类似于 Java 的 @Nullable T
- TypeVar 可以绑定多个类型，用逗号分隔
"""

from typing import Dict, Generic, Iterable, List, Optional, Tuple, TypeVar

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BSP_TYPE
from Common.func_util import has_overlap
from Seg.Seg import CSeg
from Seg.SegListComm import CSegListComm
from ZS.ZS import CZS

from .BS_Point import CBS_Point
from .BSPointConfig import CBSPointConfig, CPointConfig

LINE_TYPE = TypeVar('LINE_TYPE', CBi, CSeg[CBi])
LINE_LIST_TYPE = TypeVar('LINE_LIST_TYPE', CBiList, CSegListComm[CBi])


class CBSPointList(Generic[LINE_TYPE, LINE_LIST_TYPE]):
    """
    买卖点列表 - 管理买卖点的计算和存储

    缠论知识 - 买卖点计算流程：
    1. 第一类买卖点（T1）：中枢背驰
       - 离开中枢的笔力度 < 进入中枢的笔力度
       - 出现背驰 → 第一类买卖点
    2. 第二类买卖点（T2）：回测中枢
       - 第一类买卖点后，反向笔回测中枢不破
       - 回撤率 < max_bs2_rate → 第二类买卖点
    3. 第三类买卖点（T3A/T3B）：突破中枢
       - 离开中枢的笔突破中枢后，回测不破中枢
       - T3A: 中枢之后形成
       - T3B: 中枢之前形成（盘整背驰）

    属性说明：
    - bsp_store_dict: 按类型存储买卖点的字典
    - bsp_store_flat_dict: 按笔索引存储买卖点的字典（去重）
    - bsp1_list: 第一类买卖点列表
    - bsp1_dict: 第一类买卖点字典（按笔索引）
    - config: 买卖点配置
    - last_sure_pos: 最后一个确认位置
    """

    def __init__(self, bs_point_config: CBSPointConfig):
        """
        初始化买卖点列表

        数据结构：
        - bsp_store_dict: {BSP_TYPE: ([buy_list], [sell_list])}
        - bsp_store_flat_dict: {bi_idx: CBS_Point}
        """
        self.bsp_store_dict: Dict[BSP_TYPE, Tuple[List[CBS_Point[LINE_TYPE]], List[CBS_Point[LINE_TYPE]]]] = {}
        self.bsp_store_flat_dict: Dict[int, CBS_Point[LINE_TYPE]] = {}

        self.bsp1_list: List[CBS_Point[LINE_TYPE]] = []
        self.bsp1_dict: Dict[int, CBS_Point[LINE_TYPE]] = {}

        self.config = bs_point_config
        self.last_sure_pos = -1
        self.last_sure_seg_idx = 0

    def store_add_bsp(self, bsp_type: BSP_TYPE, bsp: CBS_Point[LINE_TYPE]):
        """
        存储买卖点

        参数:
            bsp_type: 买卖点类型
            bsp: 买卖点对象

        存储结构：
        - bsp_store_dict[bsp_type][is_buy]: 按类型和买卖方向存储
        - bsp_store_flat_dict[bi.idx]: 按笔索引存储（用于去重）
        """
        if bsp_type not in self.bsp_store_dict:
            self.bsp_store_dict[bsp_type] = ([], [])
        if len(self.bsp_store_dict[bsp_type][bsp.is_buy]) > 0:
            assert self.bsp_store_dict[bsp_type][bsp.is_buy][-1].bi.idx < bsp.bi.idx, \
                f"{bsp_type}, {bsp.is_buy} {self.bsp_store_dict[bsp_type][bsp.is_buy][-1].bi.idx} {bsp.bi.idx}"
        self.bsp_store_dict[bsp_type][bsp.is_buy].append(bsp)
        self.bsp_store_flat_dict[bsp.bi.idx] = bsp

    def add_bsp1(self, bsp: CBS_Point[LINE_TYPE]):
        """添加第一类买卖点"""
        if len(self.bsp1_list) > 0:
            assert self.bsp1_list[-1].bi.idx < bsp.bi.idx
        self.bsp1_list.append(bsp)
        self.bsp1_dict[bsp.bi.idx] = bsp

    def clear_store_end(self):
        """
        清理末尾失效的买卖点（增量更新时使用）

        当新数据到来后，末尾的买卖点可能失效，需要清理。
        清理所有类型中 last_sure_pos 之后的买卖点。

        同时清理买卖点对应的笔的 bsp 引用。
        """
        for bsp_list in self.bsp_store_dict.values():
            for is_buy in [True, False]:
                while len(bsp_list[is_buy]) > 0:
                    if bsp_list[is_buy][-1].bi.get_end_klu().idx <= self.last_sure_pos:
                        break
                    del self.bsp_store_flat_dict[bsp_list[is_buy][-1].bi.idx]
                    bsp_list[is_buy][-1].bi.bsp = None  # 清空笔的买卖点引用
                    bsp_list[is_buy].pop()

    def clear_bsp1_end(self):
        """清理末尾失效的第一类买卖点"""
        while len(self.bsp1_list) > 0:
            if self.bsp1_list[-1].bi.get_end_klu().idx <= self.last_sure_pos:
                break
            del self.bsp1_dict[self.bsp1_list[-1].bi.idx]
            self.bsp1_list.pop()

    def bsp_iter(self) -> Iterable[CBS_Point[LINE_TYPE]]:
        """
        遍历所有买卖点（先买入后卖出）

        Python 语法：yield from 是生成器委托
        Java 对比：类似于 flatMap 后的迭代器
        """
        for bsp_list in self.bsp_store_dict.values():
            yield from bsp_list[True]   # 所有买入点
            yield from bsp_list[False]  # 所有卖出点

    def bsp_iter_v2(self) -> Iterable[CBS_Point[LINE_TYPE]]:
        """
        按笔索引降序遍历所有买卖点（最新的在前）

        算法：维护一个多路归并的索引列表，每次找最大的笔索引。
        类似于多路归并排序中的归并过程。

        Java 对比：类似于 PriorityQueue + 多路归并
        """
        list_indices = []
        for bsp_type, bsp_list in self.bsp_store_dict.items():
            if bsp_list[True]:
                list_indices.append([bsp_type, True, len(bsp_list[True]) - 1])
            if bsp_list[False]:
                list_indices.append([bsp_type, False, len(bsp_list[False]) - 1])

        while list_indices:
            max_idx = -1
            max_bi_idx = -1
            max_bsp = None

            # 找当前所有列表中笔索引最大的买卖点
            for i, (bsp_type, is_buy, idx) in enumerate(list_indices):
                if idx >= 0:
                    bsp = self.bsp_store_dict[bsp_type][is_buy][idx]
                    if bsp.bi.idx > max_bi_idx:
                        max_bi_idx = bsp.bi.idx
                        max_idx = i
                        max_bsp = bsp

            if max_bsp is None:
                break

            yield max_bsp
            list_indices[max_idx][2] -= 1
            if list_indices[max_idx][2] < 0:
                list_indices.pop(max_idx)

    def __len__(self):
        return len(self.bsp_store_flat_dict)

    def cal(self, bi_list: LINE_LIST_TYPE, seg_list: CSegListComm[LINE_TYPE]):
        """
        计算所有买卖点（核心入口方法）

        参数:
            bi_list: 笔列表（或线段列表）
            seg_list: 线段列表

        计算顺序：
        1. 清理末尾失效买卖点
        2. 计算第一类买卖点（cal_seg_bs1point）
        3. 计算第二类买卖点（cal_seg_bs2point）
        4. 计算第三类买卖点（cal_seg_bs3point）
        5. 更新最后确认位置
        """
        self.clear_store_end()
        self.clear_bsp1_end()
        self.cal_seg_bs1point(seg_list, bi_list)
        self.cal_seg_bs2point(seg_list, bi_list)
        self.cal_seg_bs3point(seg_list, bi_list)

        self.update_last_pos(seg_list)

    def update_last_pos(self, seg_list: CSegListComm):
        """更新最后一个确认位置（用于增量更新）"""
        self.last_sure_pos = -1
        self.last_sure_seg_idx = 0
        seg_idx = len(seg_list)-1
        while seg_idx >= 0:
            seg = seg_list[seg_idx]
            if seg.is_sure:
                self.last_sure_pos = seg.end_bi.get_begin_klu().idx
                self.last_sure_seg_idx = seg.idx
                return
            seg_idx -= 1

    def seg_need_cal(self, seg: CSeg):
        """判断线段是否需要重新计算买卖点"""
        return seg.end_bi.get_end_klu().idx > self.last_sure_pos

    def add_bs(
        self,
        bs_type: BSP_TYPE,
        bi: LINE_TYPE,
        relate_bsp1: Optional[CBS_Point],
        is_target_bsp: bool = True,
        feature_dict=None,
    ):
        """
        添加买卖点

        参数:
            bs_type: 买卖点类型
            bi: 买卖点所在的笔
            relate_bsp1: 关联的第一类买卖点
            is_target_bsp: 是否是目标买卖点类型（配置中指定的）
            feature_dict: 特征数据

        逻辑：
        1. 如果该笔已有买卖点，添加新类型
        2. 如果 bs_type 不在配置的目标类型中，不存储
        3. 如果是 T1 或 T1P，加入 bsp1 列表
        """
        is_buy = bi.is_down()
        if exist_bsp := self.bsp_store_flat_dict.get(bi.idx):
            # 该笔已有买卖点，添加新类型
            assert exist_bsp.is_buy == is_buy
            exist_bsp.add_another_bsp_prop(bs_type, relate_bsp1)
            if feature_dict is not None:
                exist_bsp.add_feat(feature_dict)
            return
        if bs_type not in self.config.GetBSConfig(is_buy).target_types:
            is_target_bsp = False

        if is_target_bsp or bs_type in [BSP_TYPE.T1, BSP_TYPE.T1P]:
            bsp = CBS_Point[LINE_TYPE](
                bi=bi,
                is_buy=is_buy,
                bs_type=bs_type,
                relate_bsp1=relate_bsp1,
                feature_dict=feature_dict,
            )
        else:
            return
        if is_target_bsp:
            self.store_add_bsp(bs_type, bsp)
        else:
            bsp.bi.bsp = None
        if bs_type in [BSP_TYPE.T1, BSP_TYPE.T1P]:
            self.add_bsp1(bsp)

    def cal_seg_bs1point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        """
        计算第一类买卖点

        遍历所有线段，对每个线段调用 cal_single_bs1point。
        """
        for seg in seg_list[self.last_sure_seg_idx:]:
            if not self.seg_need_cal(seg):
                continue
            self.cal_single_bs1point(seg, bi_list)

    def cal_single_bs1point(self, seg: CSeg[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        """
        计算单个线段的第一类买卖点

        参数:
            seg: 线段
            bi_list: 笔列表

        两种情况：
        1. 有中枢且离开笔突破中枢：标准第一类买卖点（T1）
        2. 无中枢但有背驰：盘整背驰买卖点（T1P）

        缠论知识 - 第一类买卖点判断：
        - 中枢数量 >= min_zs_cnt
        - 离开笔 MACD 指标 < 进入笔 MACD 指标 * divergence_rate（背驰）
        """
        BSP_CONF = self.config.GetBSConfig(seg.is_down())
        zs_cnt = seg.get_multi_bi_zs_cnt() if BSP_CONF.bsp1_only_multibi_zs else len(seg.zs_lst)
        is_target_bsp = (BSP_CONF.min_zs_cnt <= 0 or zs_cnt >= BSP_CONF.min_zs_cnt)
        if len(seg.zs_lst) > 0 and \
           not seg.zs_lst[-1].is_one_bi_zs() and \
           ((seg.zs_lst[-1].bi_out and seg.zs_lst[-1].bi_out.idx >= seg.end_bi.idx) or \
            seg.zs_lst[-1].bi_lst[-1].idx >= seg.end_bi.idx) \
           and seg.end_bi.idx - seg.zs_lst[-1].get_bi_in().idx > 2:
            # 标准第一类买卖点：有中枢+背驰
            self.treat_bsp1(seg, BSP_CONF, is_target_bsp)
        else:
            # 盘整背驰：无中枢但最后一笔与前前笔背驰
            self.treat_pz_bsp1(seg, BSP_CONF, bi_list, is_target_bsp)

    def treat_bsp1(self, seg: CSeg[LINE_TYPE], BSP_CONF: CPointConfig, is_target_bsp: bool):
        """
        处理标准第一类买卖点（中枢背驰）

        判断逻辑：
        1. 离开笔是否是极值（如果 bs1_peak=True）
        2. 中枢是否发生背驰（is_divergence）
        3. 如果背驰，创建 T1 买卖点
        """
        last_zs = seg.zs_lst[-1]
        break_peak, _ = last_zs.out_bi_is_peak(seg.end_bi.idx)
        if BSP_CONF.bs1_peak and not break_peak:
            is_target_bsp = False
        is_diver, divergence_rate = last_zs.is_divergence(BSP_CONF, out_bi=seg.end_bi)
        if not is_diver:
            is_target_bsp = False
        feature_dict = {
            'divergence_rate': divergence_rate,
            'zs_cnt': len(seg.zs_lst),
        }
        self.add_bs(bs_type=BSP_TYPE.T1, bi=seg.end_bi, relate_bsp1=None, is_target_bsp=is_target_bsp, feature_dict=feature_dict)

    def treat_pz_bsp1(self, seg: CSeg[LINE_TYPE], BSP_CONF: CPointConfig, bi_list: LINE_LIST_TYPE, is_target_bsp):
        """
        处理盘整背驰买卖点（T1P）

        判断逻辑：
        1. 最后两笔必须在同一线段内
        2. 最后两笔方向必须与线段方向一致
        3. 最后一笔必须创新高/新低
        4. 最后一笔的 MACD 指标 < 前前笔的 MACD 指标（背驰）
        """
        last_bi = seg.end_bi
        pre_bi = bi_list[last_bi.idx-2]
        if last_bi.seg_idx != pre_bi.seg_idx:
            return
        if last_bi.dir != seg.dir:
            return
        if last_bi.is_down() and last_bi._low() > pre_bi._low():  # 没有创新低
            return
        if last_bi.is_up() and last_bi._high() < pre_bi._high():  # 没有创新高
            return
        in_metric = pre_bi.cal_macd_metric(BSP_CONF.macd_algo, is_reverse=False)
        out_metric = last_bi.cal_macd_metric(BSP_CONF.macd_algo, is_reverse=True)
        is_diver, divergence_rate = out_metric <= BSP_CONF.divergence_rate*in_metric, out_metric/(in_metric+1e-7)
        if not is_diver:
            is_target_bsp = False
        feature_dict = {
            'divergence_rate': divergence_rate,
            'bsp1_bi_amp': last_bi.amp(),
        }
        self.add_bs(bs_type=BSP_TYPE.T1P, bi=last_bi, relate_bsp1=None, is_target_bsp=is_target_bsp, feature_dict=feature_dict)

    def cal_seg_bs2point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        """
        计算第二类买卖点

        遍历线段，对每个线段调用 treat_bsp2。

        第二类买卖点：第一类买卖点后，回测中枢不破。
        """
        for seg in seg_list[self.last_sure_seg_idx:]:
            config = self.config.GetBSConfig(seg.is_down())
            if BSP_TYPE.T2 not in config.target_types and BSP_TYPE.T2S not in config.target_types:
                continue
            if not self.seg_need_cal(seg):
                continue
            self.treat_bsp2(seg, seg_list, bi_list)

    def treat_bsp2(self, seg: CSeg, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        """
        处理第二类买卖点

        判断逻辑：
        1. 找到第一类买卖点后的反向笔（break_bi）
        2. 再往后一笔（bsp2_bi）回测中枢
        3. 回撤率 = bsp2_bi振幅 / break_bi振幅
        4. 回撤率 < max_bs2_rate → 第二类买卖点

        缠论知识 - 第二类买卖点：
        第一类买卖点后，价格反向运动形成 break_bi，
        然后再次反向（回测方向）形成 bsp2_bi。
        如果 bsp2_bi 的回撤幅度小于 break_bi 的一定比例，
        说明中枢支撑/压力有效，形成第二类买卖点。
        """
        if len(seg_list) > 1:
            BSP_CONF = self.config.GetBSConfig(seg.is_down())
            bsp1_bi = seg.end_bi
            real_bsp1 = self.bsp1_dict.get(bsp1_bi.idx)
            if bsp1_bi.idx + 2 >= len(bi_list):
                return
            break_bi = bi_list[bsp1_bi.idx + 1]  # 第一类后的反向笔
            bsp2_bi = bi_list[bsp1_bi.idx + 2]   # 再反向的回测笔
        else:
            # 第一条线段（没有前面的线段）
            BSP_CONF = self.config.GetBSConfig(seg.is_up())
            bsp1_bi, real_bsp1 = None, None
            if len(bi_list) == 1:
                return
            bsp2_bi = bi_list[1]
            break_bi = bi_list[0]

        if BSP_CONF.bsp2_follow_1 and (not bsp1_bi or bsp1_bi.idx not in self.bsp_store_flat_dict):
            return

        retrace_rate = bsp2_bi.amp()/break_bi.amp()
        bsp2_flag = retrace_rate <= BSP_CONF.max_bs2_rate

        if bsp2_flag:
            feature_dict = {
                'bsp2_retrace_rate': retrace_rate,
                'bsp2_break_bi_amp': break_bi.amp(),
                'bsp2_bi_amp': bsp2_bi.amp(),
            }
            self.add_bs(bs_type=BSP_TYPE.T2, bi=bsp2_bi, relate_bsp1=real_bsp1, feature_dict=feature_dict)
        elif BSP_CONF.bsp2s_follow_2:
            return

        if BSP_TYPE.T2S not in self.config.GetBSConfig(seg.is_down()).target_types:
            return
        self.treat_bsp2s(seg_list, bi_list, bsp2_bi, break_bi, real_bsp1, BSP_CONF)

    def treat_bsp2s(
        self,
        seg_list: CSegListComm,
        bi_list: LINE_LIST_TYPE,
        bsp2_bi: LINE_TYPE,
        break_bi: LINE_TYPE,
        real_bsp1: Optional[CBS_Point],
        BSP_CONF: CPointConfig,
    ):
        """
        处理类二买卖点（T2S）

        类二买卖点：中枢内多次回测形成的买卖点。

        从 bsp2_bi 开始，每隔2笔（同向笔）检查：
        1. 是否在同一线段内
        2. 是否与前一回测笔有重叠区间
        3. 是否突破了 break_bi 的端点
        4. 回撤率是否 < max_bs2_rate

        缠论知识 - 类二买卖点：
        中枢内可以多次回测，每次回测都可能形成类二买卖点。
        类二买卖点的级别比第二类买卖点低，但数量更多。
        """
        bias = 2
        _low, _high = None, None
        while bsp2_bi.idx + bias < len(bi_list):
            bsp2s_bi = bi_list[bsp2_bi.idx + bias]
            assert bsp2s_bi.seg_idx is not None and bsp2_bi.seg_idx is not None
            if BSP_CONF.max_bsp2s_lv is not None and bias/2 > BSP_CONF.max_bsp2s_lv:
                break
            if bsp2s_bi.seg_idx != bsp2_bi.seg_idx and \
               (bsp2s_bi.seg_idx < len(seg_list)-1 or bsp2s_bi.seg_idx - bsp2_bi.seg_idx >= 2 or seg_list[bsp2_bi.seg_idx].is_sure):
                break
            if bias == 2:
                if not has_overlap(bsp2_bi._low(), bsp2_bi._high(), bsp2s_bi._low(), bsp2s_bi._high()):
                    break
                _low = max([bsp2_bi._low(), bsp2s_bi._low()])
                _high = min([bsp2_bi._high(), bsp2s_bi._high()])
            elif not has_overlap(_low, _high, bsp2s_bi._low(), bsp2s_bi._high()):
                break

            if bsp2s_break_bsp1(bsp2s_bi, break_bi):
                break
            retrace_rate = abs(bsp2s_bi.get_end_val()-break_bi.get_end_val())/break_bi.amp()
            if retrace_rate > BSP_CONF.max_bs2_rate:
                break
            feature_dict = {
                'bsp2s_retrace_rate': retrace_rate,
                'bsp2s_break_bi_amp': break_bi.amp(),
                'bsp2s_bi_amp': bsp2s_bi.amp(),
                'bsp2s_lv': bias/2,
            }
            self.add_bs(bs_type=BSP_TYPE.T2S, bi=bsp2s_bi, relate_bsp1=real_bsp1, feature_dict=feature_dict)
            bias += 2

    def cal_seg_bs3point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        """
        计算第三类买卖点

        遍历线段，对每个线段检查 T3A 和 T3B 类型。

        缠论知识 - 第三类买卖点：
        离开中枢的笔突破中枢后，回测不破中枢的区间。
        - T3A: 中枢之后形成（下一个线段中）
        - T3B: 中枢之前形成（同一线段中，盘整背驰后的第三类）
        """
        for seg in seg_list[self.last_sure_seg_idx:]:
            if not self.seg_need_cal(seg):
                continue
            config = self.config.GetBSConfig(seg.is_down())
            if BSP_TYPE.T3A not in config.target_types and BSP_TYPE.T3B not in config.target_types:
                continue
            if len(seg_list) > 1:
                bsp1_bi = seg.end_bi
                bsp1_bi_idx = bsp1_bi.idx
                BSP_CONF = self.config.GetBSConfig(seg.is_down())
                real_bsp1 = self.bsp1_dict.get(bsp1_bi.idx)
                next_seg_idx = seg.idx+1
                next_seg = seg.next
            else:
                next_seg = seg
                next_seg_idx = seg.idx
                bsp1_bi, real_bsp1 = None, None
                bsp1_bi_idx = -1
                BSP_CONF = self.config.GetBSConfig(seg.is_up())
            if BSP_CONF.bsp3_follow_1 and (not bsp1_bi or bsp1_bi.idx not in self.bsp_store_flat_dict):
                continue
            if next_seg:
                self.treat_bsp3_after(seg_list, next_seg, BSP_CONF, bi_list, real_bsp1, bsp1_bi_idx, next_seg_idx)
            self.treat_bsp3_before(seg_list, seg, next_seg, bsp1_bi, BSP_CONF, bi_list, real_bsp1, next_seg_idx)

    def treat_bsp3_after(
        self,
        seg_list: CSegListComm[LINE_TYPE],
        next_seg: CSeg[LINE_TYPE],
        BSP_CONF: CPointConfig,
        bi_list: LINE_LIST_TYPE,
        real_bsp1,
        bsp1_bi_idx,
        next_seg_idx
    ):
        """
        处理第三类A买卖点（T3A：中枢之后）

        在下一条线段中找中枢后的回测笔：
        1. 遍历下一条线段中的所有多笔中枢
        2. 每个中枢的 bi_out 之后的第一笔如果回测不破中枢 → T3A
        3. bsp3a_max_zs_cnt 限制最多检查的中枢数量
        """
        first_zs = next_seg.get_first_multi_bi_zs()
        if first_zs is None:
            return
        if BSP_CONF.strict_bsp3 and first_zs.get_bi_in().idx != bsp1_bi_idx+1:
            return

        config = self.config.GetBSConfig(next_seg.is_down())
        bsp3a_max_zs_cnt = config.bsp3a_max_zs_cnt
        for zs_idx, zs in enumerate(next_seg.get_multi_bi_zs_lst()):
            if zs_idx >= bsp3a_max_zs_cnt:
                break
            if zs.bi_out is None or zs.bi_out.idx+1 >= len(bi_list):
                break
            bsp3_bi = bi_list[zs.bi_out.idx+1]
            if bsp3_bi.parent_seg is None:
                if next_seg.idx != len(seg_list)-1:
                    break
            elif bsp3_bi.parent_seg.idx != next_seg.idx:
                if len(bsp3_bi.parent_seg.bi_list) >= 3:
                    break
            if bsp3_bi.dir == next_seg.dir:
                break
            if bsp3_bi.seg_idx != next_seg_idx and next_seg_idx < len(seg_list)-2:
                break
            if bsp3_back2zs(bsp3_bi, zs):
                continue
            bsp3_peak_zs = bsp3_break_zspeak(bsp3_bi, zs)
            if BSP_CONF.bsp3_peak and not bsp3_peak_zs:
                continue
            feature_dict = {
                'bsp3_zs_height': (zs.high - zs.low)/zs.low,
                'bsp3_bi_amp': bsp3_bi.amp(),
            }
            self.add_bs(bs_type=BSP_TYPE.T3A, bi=bsp3_bi, relate_bsp1=real_bsp1, feature_dict=feature_dict)

    def treat_bsp3_before(
        self,
        seg_list: CSegListComm[LINE_TYPE],
        seg: CSeg[LINE_TYPE],
        next_seg: Optional[CSeg[LINE_TYPE]],
        bsp1_bi: Optional[LINE_TYPE],
        BSP_CONF: CPointConfig,
        bi_list: LINE_LIST_TYPE,
        real_bsp1,
        next_seg_idx
    ):
        """
        处理第三类B买卖点（T3B：中枢之前）

        在同一线段中，中枢形成后，离开笔突破中枢然后回测不破 → T3B。
        只取第一个满足条件的回测笔。
        """
        cmp_zs = seg.get_final_multi_bi_zs()
        if cmp_zs is None:
            return
        if not bsp1_bi:
            return
        if BSP_CONF.strict_bsp3 and (cmp_zs.bi_out is None or cmp_zs.bi_out.idx != bsp1_bi.idx):
            return
        end_bi_idx = cal_bsp3_bi_end_idx(next_seg)
        for bsp3_bi in bi_list[bsp1_bi.idx+2::2]:  # 每隔2笔取一笔（同向笔）
            if bsp3_bi.idx > end_bi_idx:
                break
            assert bsp3_bi.seg_idx is not None
            if bsp3_bi.seg_idx != next_seg_idx and bsp3_bi.seg_idx < len(seg_list)-1:
                break
            if bsp3_back2zs(bsp3_bi, cmp_zs):
                continue
            feature_dict = {
                'bsp3_zs_height': (cmp_zs.high - cmp_zs.low)/cmp_zs.low,
                'bsp3_bi_amp': bsp3_bi.amp(),
            }
            self.add_bs(bs_type=BSP_TYPE.T3B, bi=bsp3_bi, relate_bsp1=real_bsp1, feature_dict=feature_dict)
            break  # 只取第一个满足条件的

    def getSortedBspList(self) -> List[CBS_Point[LINE_TYPE]]:
        """
        获取按笔索引排序的买卖点列表

        Python 语法：sorted(iterable, key=lambda ...)
        Java 对比：stream.sorted(Comparator.comparing(bsp -> bsp.bi.idx)).collect(toList())
        """
        return sorted(self.bsp_iter(), key=lambda bsp: bsp.bi.idx)

    def get_latest_bsp(self, number: int) -> List[CBS_Point[LINE_TYPE]]:
        """
        获取最新的 N 个买卖点（按笔索引降序）

        参数:
            number: 获取数量，0 表示获取全部

        返回:
            最新的买卖点列表
        """
        res = []
        for bsp in self.bsp_iter_v2():
            res.append(bsp)
            if number != 0 and len(res) >= number:
                break
        return res


def bsp2s_break_bsp1(bsp2s_bi: LINE_TYPE, bsp2_break_bi: LINE_TYPE) -> bool:
    """
    判断类二买卖点是否突破了第一类买卖点后的反向笔

    返回:
        True 如果突破了（类二买卖点不再有效）
    """
    return (bsp2s_bi.is_down() and bsp2s_bi._low() < bsp2_break_bi._low()) or \
           (bsp2s_bi.is_up() and bsp2s_bi._high() > bsp2_break_bi._high())


def bsp3_back2zs(bsp3_bi: LINE_TYPE, zs: CZS) -> bool:
    """
    判断第三类买卖点是否回到了中枢区间内

    返回:
        True 如果回到了中枢区间（第三类买卖点不成立）
    """
    return (bsp3_bi.is_down() and bsp3_bi._low() < zs.high) or \
           (bsp3_bi.is_up() and bsp3_bi._high() > zs.low)


def bsp3_break_zspeak(bsp3_bi: LINE_TYPE, zs: CZS) -> bool:
    """
    判断第三类买卖点是否突破了中枢的极值区间

    返回:
        True 如果突破了中枢极值
    """
    return (bsp3_bi.is_down() and bsp3_bi._high() >= zs.peak_high) or \
           (bsp3_bi.is_up() and bsp3_bi._low() <= zs.peak_low)


def cal_bsp3_bi_end_idx(seg: Optional[CSeg[LINE_TYPE]]):
    """
    计算第三类B买卖点的结束笔索引

    返回:
        结束笔索引，如果找不到则返回 float("inf")
    """
    if not seg:
        return float("inf")
    if seg.get_multi_bi_zs_cnt() == 0 and seg.next is None:
        return float("inf")
    end_bi_idx = seg.end_bi.idx-1
    for zs in seg.zs_lst:
        if zs.is_one_bi_zs():
            continue
        if zs.bi_out is not None:
            end_bi_idx = zs.bi_out.idx
            break
    return end_bi_idx