# -*- coding: utf-8 -*-
"""
绘图元数据模块 - 将分析对象转换为绘图用的元数据结构

Java 开发者注意：
- Python 的 List[XXX] 是泛型类型提示，类似于 Java 的 List<XXX>
- Python 的 assert 断言语句，类似于 Java 的 assert 关键字
  但 Python 的 assert 在 -O 模式下会被优化掉，不能用于业务逻辑校验
- Python 的 isinstance(obj, Type) 类似于 Java 的 obj instanceof Type
- Python 的 yield from 是生成器委托，类似于 Java Stream 的 flatMap
- Python 的列表推导式 [expr for x in list] 类似于 Java 的 stream().map().collect()
"""

from typing import List

from Bi.Bi import CBi
from BuySellPoint.BS_Point import CBS_Point
from Common.CEnum import FX_TYPE
from KLine.KLine import CKLine
from KLine.KLine_List import CKLine_List
from Seg.Eigen import CEigen
from Seg.EigenFX import CEigenFX
from Seg.Seg import CSeg
from ZS.ZS import CZS


class Cklc_meta:
    """
    合并K线元数据 - 从 CKLine（合并K线）提取绘图所需信息

    缠论知识 - 合并K线：
    合并K线是经过包含处理后的K线，多根原始K线可能合并为一根。
    合并K线是分型和笔的基础。
    """

    def __init__(self, klc: CKLine):
        self.high = klc.high
        self.low = klc.low
        self.begin_idx = klc.lst[0].idx    # 第一根原始K线的索引
        self.end_idx = klc.lst[-1].idx     # 最后一根原始K线的索引
        # 分型类型：如果是分型则用分型类型，否则用K线方向
        self.type = klc.fx if klc.fx != FX_TYPE.UNKNOWN else klc.dir

        self.klu_list = list(klc.lst)       # 原始K线列表


class CBi_meta:
    """
    笔元数据 - 从 CBi（笔）提取绘图所需信息

    缠论知识 - 笔：
    笔是缠论的基本构件，连接相邻的顶分型和底分型。
    确定笔（is_sure=True）用实线绘制，虚拟笔用虚线绘制。
    """

    def __init__(self, bi: CBi):
        self.idx = bi.idx
        self.dir = bi.dir
        self.type = bi.type
        self.begin_x = bi.get_begin_klu().idx   # 笔起始K线索引
        self.end_x = bi.get_end_klu().idx        # 笔结束K线索引
        self.begin_y = bi.get_begin_val()        # 笔起始价格
        self.end_y = bi.get_end_val()            # 笔结束价格
        self.is_sure = bi.is_sure                 # 是否已确认


class CSeg_meta:
    """
    线段元数据 - 从 CSeg（线段）提取绘图所需信息

    缠论知识 - 线段：
    线段是由至少三笔组成的更大级别的结构。
    当 seg.start_bi 是 CSeg 时，说明这是线段构成的线段（更高级别）。

    参数:
        seg: CSeg 对象（笔线段或线段线段）
    """

    def __init__(self, seg: CSeg):
        # 判断线段是由笔构成还是由线段构成
        # Python 特性：isinstance 检查对象类型
        # Java 对比：seg.start_bi instanceof CBi
        if isinstance(seg.start_bi, CBi):
            self.begin_x = seg.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.get_begin_val()
            self.end_x = seg.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.get_end_val()
        else:
            # 线段构成的线段（segseg），需要多取一层
            assert isinstance(seg.start_bi, CSeg)
            self.begin_x = seg.start_bi.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.start_bi.get_begin_val()
            self.end_x = seg.end_bi.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.end_bi.get_end_val()
        self.dir = seg.dir
        self.is_sure = seg.is_sure
        self.idx = seg.idx

        # 趋势线数据
        self.tl = {}
        if seg.support_trend_line and seg.support_trend_line.line:
            self.tl["support"] = seg.support_trend_line   # 支撑线
        if seg.resistance_trend_line and seg.resistance_trend_line.line:
            self.tl["resistance"] = seg.resistance_trend_line  # 阻力线

    def format_tl(self, tl):
        """
        格式化趋势线为绘图坐标

        参数:
            tl: 趋势线对象（CTrendLine）

        返回:
            (x0, y0, x1, y1) 趋势线的起点和终点坐标

        计算逻辑：
        通过趋势线的斜率和截距，计算线段起点和终点在趋势线上的投影坐标。
        tl_slope + 1e-7 是为了避免除零错误。
        """
        assert tl.line
        tl_slope = tl.line.slope + 1e-7  # 加微小值防止除零
        tl_x = tl.line.p.x
        tl_y = tl.line.p.y
        tl_y0 = self.begin_y
        tl_y1 = self.end_y
        # 反算 x 坐标：(y - y0) / slope + x0
        tl_x0 = (tl_y0 - tl_y) / tl_slope + tl_x
        tl_x1 = (tl_y1 - tl_y) / tl_slope + tl_x
        return tl_x0, tl_y0, tl_x1, tl_y1


class CEigen_meta:
    """
    特征序列元素元数据 - 从 CEigen 提取绘图信息

    缠论知识 - 特征序列：
    特征序列是线段算法中的关键概念，将反向笔组合成特征序列元素。
    特征序列元素类似于K线，在其上寻找分型来确定线段端点。
    """

    def __init__(self, eigen: CEigen):
        self.begin_x = eigen.lst[0].get_begin_klu().idx
        self.end_x = eigen.lst[-1].get_end_klu().idx
        self.begin_y = eigen.low
        self.end_y = eigen.high
        self.w = self.end_x - self.begin_x   # 宽度
        self.h = self.end_y - self.begin_y   # 高度


class CEigenFX_meta:
    """
    特征序列分型元数据 - 从 CEigenFX 提取绘图信息

    缠论知识 - 特征序列分型：
    特征序列分型包含三个特征序列元素（左、中、右），
    中间元素是顶分型或底分型，用于确定线段的端点。
    gap 属性表示特征序列之间是否存在跳空缺口。
    """

    def __init__(self, eigenFX: CEigenFX):
        # 三个特征序列元素（ele[0] 左, ele[1] 中, ele[2] 右）
        self.ele = [CEigen_meta(ele) for ele in eigenFX.ele if ele is not None]
        assert len(self.ele) == 3
        assert eigenFX.ele[1] is not None
        self.gap = eigenFX.ele[1].gap  # 是否有跳空缺口
        self.fx = eigenFX.ele[1].fx    # 分型类型（顶/底）


class CZS_meta:
    """
    中枢元数据 - 从 CZS（中枢）提取绘图信息

    缠论知识 - 中枢：
    中枢是至少三段连续同级别线段重叠的价格区间。
    中枢的上沿是重叠区间的下沿（ZG），下沿是重叠区间的上沿（ZD）。
    中枢是判断买卖点的核心依据。
    """

    def __init__(self, zs: CZS):
        self.low = zs.low
        self.high = zs.high
        self.begin = zs.begin.idx    # 中枢起始索引
        self.end = zs.end.idx        # 中枢结束索引
        self.w = self.end - self.begin  # 宽度
        self.h = self.high - self.low   # 高度
        self.is_sure = zs.is_sure    # 是否已确认
        self.sub_zs_lst = [CZS_meta(t) for t in zs.sub_zs_lst]  # 子中枢列表
        self.is_onebi_zs = zs.is_one_bi_zs()  # 是否是单笔中枢


class CBS_Point_meta:
    """
    买卖点元数据 - 从 CBS_Point 提取绘图信息

    缠论知识 - 买卖点：
    缠论定义了多类买卖点：
    - 一买（b1）：趋势背驰后的第一类买点
    - 二买（b2）：一买后回调不破前低的买点
    - 三买（b3）：中枢上方回调不破中枢的买点
    - 一卖（s1）/二卖（s2）/三卖（s3）：对应的卖点

    参数:
        bsp: CBS_Point 买卖点对象
        is_seg: 是否是线段级别的买卖点
    """

    def __init__(self, bsp: CBS_Point, is_seg):
        self.is_buy = bsp.is_buy
        self.type = bsp.type2str()
        self.is_seg = is_seg

        self.x = bsp.klu.idx
        # 买点标记在最低价，卖点标记在最高价
        self.y = bsp.klu.low if self.is_buy else bsp.klu.high

    def desc(self):
        """
        返回买卖点的描述文本

        返回:
            如 "b1"（笔级别一买）、"※s2"（线段级别二卖）
            前缀 ※ 表示是线段级别的买卖点
        """
        is_seg_flag = "※" if self.is_seg else ""
        return f'{is_seg_flag}b{self.type}' if self.is_buy else f'{is_seg_flag}s{self.type}'


class CChanPlotMeta:
    """
    缠论绘图元数据 - 聚合一个级别的所有绘图数据

    参数:
        kl_list: CKLine_List 对象，包含该级别的所有分析结果

    将 CKLine_List 中的分析结果（笔、线段、中枢、买卖点等）
    转换为轻量级的元数据对象，供绘图使用。

    转换后的元数据对象只包含绘图所需的坐标和样式信息，
    不包含原始分析逻辑，实现了"数据"与"视图"的分离。
    """

    def __init__(self, kl_list: CKLine_List):
        self.data = kl_list

        # 合并K线元数据列表
        self.klc_list: List[Cklc_meta] = [Cklc_meta(klc) for klc in kl_list.lst]
        # 日期刻度标签
        self.datetick = [klu.time.to_str() for klu in self.klu_iter()]
        # K线总数（原始K线，非合并K线）
        self.klu_len = sum(len(klc.klu_list) for klc in self.klc_list)

        # 笔元数据列表
        self.bi_list = [CBi_meta(bi) for bi in kl_list.bi_list]

        # 线段元数据 和 特征序列分型元数据
        self.seg_list: List[CSeg_meta] = []
        self.eigenfx_lst: List[CEigenFX_meta] = []
        for seg in kl_list.seg_list:
            self.seg_list.append(CSeg_meta(seg))
            if seg.eigen_fx:
                self.eigenfx_lst.append(CEigenFX_meta(seg.eigen_fx))

        # 线段构成的线段（segseg）和其特征序列分型
        self.seg_eigenfx_lst: List[CEigenFX_meta] = []
        self.segseg_list: List[CSeg_meta] = []
        for segseg in kl_list.segseg_list:
            self.segseg_list.append(CSeg_meta(segseg))
            if segseg.eigen_fx:
                self.seg_eigenfx_lst.append(CEigenFX_meta(segseg.eigen_fx))

        # 中枢元数据（笔中枢 和 线段中枢）
        self.zs_lst: List[CZS_meta] = [CZS_meta(zs) for zs in kl_list.zs_list]
        self.segzs_lst: List[CZS_meta] = [CZS_meta(segzs) for segzs in kl_list.segzs_list]

        # 买卖点元数据（笔级别 和 线段级别）
        self.bs_point_lst: List[CBS_Point_meta] = [CBS_Point_meta(bs_point, is_seg=False) for bs_point in kl_list.bs_point_lst.bsp_iter()]
        self.seg_bsp_lst: List[CBS_Point_meta] = [CBS_Point_meta(seg_bsp, is_seg=True) for seg_bsp in kl_list.seg_bs_point_lst.bsp_iter()]

    def klu_iter(self):
        """
        迭代所有原始K线

        yield from 将迭代委托给每个 klc 的 klu_list
        Java 对比：类似于 flatMap(klc -> klc.klu_list.stream())
        """
        for klc in self.klc_list:
            yield from klc.klu_list

    def sub_last_kseg_start_idx(self, seg_cnt):
        """
        获取倒数第 N 个线段在子级别中的起始索引

        参数:
            seg_cnt: 倒数第几个线段

        返回:
            子级别K线的起始索引

        用于多级别联动绘图：当用户查看高级别最后 N 个线段时，
        低级别图表自动定位到对应的K线范围。
        """
        if seg_cnt is None or len(self.data.seg_list) <= seg_cnt:
            return 0
        else:
            return self.data.seg_list[-seg_cnt].get_begin_klu().sub_kl_list[0].idx

    def sub_last_kbi_start_idx(self, bi_cnt):
        """
        获取倒数第 N 个笔在子级别中的起始索引

        参数:
            bi_cnt: 倒数第几个笔

        返回:
            子级别K线的起始索引
        """
        if bi_cnt is None or len(self.data.bi_list) <= bi_cnt:
            return 0
        else:
            return self.data.bi_list[-bi_cnt].begin_klc.lst[0].sub_kl_list[0].idx

    def sub_range_start_idx(self, x_range):
        """
        根据K线范围获取子级别的起始索引

        参数:
            x_range: 当前级别的K线显示范围

        返回:
            子级别对应的起始K线索引

        从当前级别的最后开始倒推 x_range 根K线，找到对应的子级别起始位置。
        这确保多级别图表的时间范围对齐。
        """
        for klc in self.data[::-1]:     # 从后往前遍历合并K线
            for klu in klc[::-1]:       # 从后往前遍历原始K线
                x_range -= 1
                if x_range == 0:
                    return klu.sub_kl_list[0].idx
        return 0