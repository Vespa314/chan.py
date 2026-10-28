# -*- coding: utf-8 -*-
"""
K线列表模块 - 管理某一级别的所有 K 线、笔、线段、中枢、买卖点

Java 开发者注意：
- Python 的 @overload 装饰器仅用于类型提示，不影响运行时行为
  Java 对比：Java 直接写多个重载方法签名
- yield from 是 Python 生成器委托语法，产出迭代器中的每个元素
  Java 对比：类似于 Iterator 的 flatMap 或 Stream.flatMap()
- copy.deepcopy 类似于 Java 中实现 Cloneable 接口 + 递归深拷贝
- Python 可以在函数内 import（延迟导入），避免循环引用
  Java 对比：Java 的 import 是编译时确定的，不支持延迟导入
"""

import copy
from typing import List, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from BuySellPoint.BSPointList import CBSPointList
from ChanConfig import CChanConfig
from Common.CEnum import KLINE_DIR, SEG_TYPE
from Common.ChanException import CChanException, ErrCode
from Seg.Seg import CSeg
from Seg.SegConfig import CSegConfig
from Seg.SegListComm import CSegListComm
from ZS.ZSList import CZSList

from .KLine import CKLine
from .KLine_Unit import CKLine_Unit


def get_seglist_instance(seg_config: CSegConfig, lv) -> CSegListComm:
    """
    工厂方法：根据配置创建线段列表实例

    参数:
        seg_config: 线段配置
        lv: 线段层级（SEG_TYPE.BI 表示笔的线段，SEG_TYPE.SEG 表示线段的线段）

    返回:
        对应算法的线段列表实例

    三种线段算法：
    - "chan": 特征序列法（默认，推荐使用）
    - "1+1": 1+1 终结法（已废弃）
    - "break": 线段破坏法（已废弃）

    Python 特性：函数内 import 是延迟导入，只有在需要时才加载对应模块
    Java 对比：Java 中 import 是类级别的，这种延迟加载需要用反射或工厂模式实现
    """
    if seg_config.seg_algo == "chan":
        from Seg.SegListChan import CSegListChan
        return CSegListChan(seg_config, lv)
    elif seg_config.seg_algo == "1+1":
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from Seg.SegListDYH import CSegListDYH
        return CSegListDYH(seg_config, lv)
    elif seg_config.seg_algo == "break":
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from Seg.SegListDef import CSegListDef
        return CSegListDef(seg_config, lv)
    else:
        raise CChanException(f"unsupport seg algoright:{seg_config.seg_algo}", ErrCode.PARA_ERROR)


class CKLine_List:
    """
    K线列表 - 某一级别下所有数据的容器

    这是连接所有分析模块的枢纽类，管理：
    - K线列表（lst: List[CKLine]）
    - 笔列表（bi_list）
    - 线段列表（seg_list: 笔的线段）
    - 线段线段列表（segseg_list: 线段的线段）
    - 中枢列表（zs_list: 笔中枢，segzs_list: 线段中枢）
    - 买卖点列表（bs_point_lst: 笔买卖点，seg_bs_point_lst: 线段买卖点）

    缠论知识 - 递归层次：
    笔由K线构成 → 线段由笔构成 → 中枢由线段构成 → 买卖点由中枢+线段构成
    这就是从微观到宏观的递归分析过程。

    属性说明：
    - kl_type: K线级别（日线/30分钟/5分钟等）
    - config: 全局配置
    - step_calculation: 是否逐根计算（trigger_step 模式）
    - last_sure_seg_start_bi_idx: 最后一个确认的线段起始笔索引
    """

    def __init__(self, kl_type, conf: CChanConfig):
        """初始化K线列表"""
        self.kl_type = kl_type
        self.config = conf
        self.lst: List[CKLine] = []  # K线列表，元素为合并后的K线（CKLine类型）

        # 创建各分析层次的列表对象
        self.bi_list = CBiList(bi_conf=conf.bi_conf)
        self.seg_list: CSegListComm[CBi] = get_seglist_instance(seg_config=conf.seg_conf, lv=SEG_TYPE.BI)
        self.segseg_list: CSegListComm[CSeg[CBi]] = get_seglist_instance(seg_config=conf.seg_conf, lv=SEG_TYPE.SEG)

        self.zs_list = CZSList(zs_config=conf.zs_conf)
        self.segzs_list = CZSList(zs_config=conf.zs_conf)

        self.bs_point_lst = CBSPointList[CBi, CBiList](bs_point_config=conf.bs_point_conf)
        self.seg_bs_point_lst = CBSPointList[CSeg, CSegListComm](bs_point_config=conf.seg_bs_point_conf)

        self.metric_model_lst = conf.GetMetricModel()

        self.step_calculation = self.need_cal_step_by_step()

        # 记录最后一个确认的线段起始笔索引，用于增量计算优化
        self.last_sure_seg_start_bi_idx = -1
        self.last_sure_segseg_start_bi_idx = -1

    def __deepcopy__(self, memo):
        """
        深拷贝整个 K 线列表及其所有子对象

        拷贝顺序：
        1. 先拷贝所有原始 K 线单元（klu）并重建链表关系
        2. 再拷贝合并 K 线（klc）并重建包含关系
        3. 拷贝笔、线段、中枢、买卖点等子对象

        Python 特性：memo 字典用于记录已拷贝的对象，防止循环引用
        Java 对比：类似于序列化/反序列化（Serializable）但更灵活
        """
        new_obj = CKLine_List(self.kl_type, self.config)
        memo[id(self)] = new_obj

        for klc in self.lst:
            # 步骤1：深拷贝所有原始 K 线单元并重建链表
            klus_new = []
            for klu in klc.lst:
                new_klu = copy.deepcopy(klu, memo)
                memo[id(klu)] = new_klu
                if klu.pre is not None:
                    new_klu.set_pre_klu(memo[id(klu.pre)])  # 重建链表关系
                klus_new.append(new_klu)

            # 步骤2：重建合并K线，逐个添加原始K线
            new_klc = CKLine(klus_new[0], idx=klc.idx, _dir=klc.dir)
            new_klc.set_fx(klc.fx)
            new_klc.kl_type = klc.kl_type
            for idx, klu in enumerate(klus_new):
                klu.set_klc(new_klc)
                if idx != 0:
                    new_klc.try_add(klu, skip_update_input=True)  # 跳过反向引用设置
            memo[id(klc)] = new_klc

            # 重建合并K线之间的链表关系
            if new_obj.lst:
                new_obj.lst[-1].set_next(new_klc)
                new_klc.set_pre(new_obj.lst[-1])
            new_obj.lst.append(new_klc)

        # 步骤3：深拷贝所有子对象
        new_obj.bi_list = copy.deepcopy(self.bi_list, memo)
        new_obj.seg_list = copy.deepcopy(self.seg_list, memo)
        new_obj.segseg_list = copy.deepcopy(self.segseg_list, memo)
        new_obj.zs_list = copy.deepcopy(self.zs_list, memo)
        new_obj.segzs_list = copy.deepcopy(self.segzs_list, memo)
        new_obj.bs_point_lst = copy.deepcopy(self.bs_point_lst, memo)
        new_obj.metric_model_lst = copy.deepcopy(self.metric_model_lst, memo)
        new_obj.step_calculation = copy.deepcopy(self.step_calculation, memo)
        new_obj.seg_bs_point_lst = copy.deepcopy(self.seg_bs_point_lst, memo)
        return new_obj

    @overload
    def __getitem__(self, index: int) -> CKLine: ...

    @overload
    def __getitem__(self, index: slice) -> List[CKLine]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CKLine], CKLine]:
        """
        支持 [] 索引访问
        Python 特性：__getitem__ 魔术方法，类似于 Java 的 List.get()
        @overload 装饰器仅用于类型提示，运行时实际执行的是这个方法
        """
        return self.lst[index]

    def __len__(self):
        """支持 len() 函数，Python 特性：类似于 Java 的 list.size()"""
        return len(self.lst)

    def cal_seg_and_zs(self):
        """
        计算线段和中枢（核心分析流程）

        处理流程：
        1. 如果非逐根模式，添加虚拟笔（处理末尾未完成的笔）
        2. 计算笔的线段（seg_list）
        3. 计算笔中枢（zs_list）
        4. 关联中枢到线段（update_zs_in_seg）
        5. 计算线段的线段（segseg_list）
        6. 计算线段中枢（segzs_list）
        7. 关联中枢到线段线段
        8. 计算买卖点（先线段买卖点，再笔买卖点）

        缠论知识 - 计算顺序：
        笔→线段→中枢→买卖点，这是从底层到高层的递进关系。
        必须先有线段才能有中枢，必须先有中枢才能有买卖点。
        """
        if not self.step_calculation:
            # 非逐根模式：在所有K线加载完成后，尝试添加虚拟笔
            self.bi_list.try_add_virtual_bi(self.lst[-1])

        # 笔→线段→中枢
        self.last_sure_seg_start_bi_idx = cal_seg(self.bi_list, self.seg_list, self.last_sure_seg_start_bi_idx)
        self.zs_list.cal_bi_zs(self.bi_list, self.seg_list)
        update_zs_in_seg(self.bi_list, self.seg_list, self.zs_list)  # 计算seg的zs_lst，以及中枢的bi_in, bi_out

        # 线段→线段线段→线段中枢
        self.last_sure_segseg_start_bi_idx = cal_seg(self.seg_list, self.segseg_list, self.last_sure_segseg_start_bi_idx)
        self.segzs_list.cal_bi_zs(self.seg_list, self.segseg_list)
        update_zs_in_seg(self.seg_list, self.segseg_list, self.segzs_list)  # 计算segseg的zs_lst，以及中枢的bi_in, bi_out

        # 计算买卖点
        self.seg_bs_point_lst.cal(self.seg_list, self.segseg_list)  # 线段线段买卖点
        self.bs_point_lst.cal(self.bi_list, self.seg_list)  # 笔买卖点

    def need_cal_step_by_step(self):
        """判断是否需要逐根K线计算模式"""
        return self.config.trigger_step

    def add_single_klu(self, klu: CKLine_Unit):
        """
        添加单根原始K线，并触发后续分析

        这是整个系统的核心入口方法。每根K线到来后：
        1. 计算指标（MACD、BOLL等）
        2. 尝试合并包含关系
        3. 如果不需要合并，检测分型、更新笔
        4. 如果笔有更新，触发线段和中枢计算

        参数:
            klu: 原始K线单元

        缠论知识 - 实时分析流程：
        每来一根新K线 → 指标计算 → 包含处理 → 分型检测 → 笔更新 → 线段更新 → 中枢更新 → 买卖点更新
        这就是逐根K线（step-by-step）的实时分析过程。

        两个触发 cal_seg_and_zs 的条件：
        条件A：新笔形成且 step_calculation=True（第132行）
        条件B：包含处理导致虚拟笔更新（第134行，参见issue#175）
        """
        klu.set_metric(self.metric_model_lst)  # 先计算所有技术指标

        if len(self.lst) == 0:
            # 第一根K线，直接创建合并K线
            self.lst.append(CKLine(klu, idx=0))
        else:
            _dir = self.lst[-1].try_add(klu)  # 尝试与上一根合并K线合并 TODO 改逻辑是标准笔的判断，还可以增加macd等逻辑判断 
            if _dir != KLINE_DIR.COMBINE:  # 不需要合并K线 → 创建新的合并K线
                self.lst.append(CKLine(klu, idx=len(self.lst), _dir=_dir))
                if len(self.lst) >= 3:
                    # 至少3根合并K线才能检测分型（需要前+中+后）
                    self.lst[-2].update_fx(self.lst[-3], self.lst[-1])
                # 更新笔列表，如果笔有更新且是逐根模式，触发完整计算
                if self.bi_list.update_bi(self.lst[-2], self.lst[-1], self.step_calculation) and self.step_calculation:
                    self.cal_seg_and_zs()
            elif self.step_calculation and self.bi_list.try_add_virtual_bi(self.lst[-1], need_del_end=True):
                # 包含处理可能影响虚拟笔的状态（参见issue#175）
                self.cal_seg_and_zs()

    def klu_iter(self, klc_begin_idx=0):
        """
        获取从指定位置开始的原始K线迭代器

        参数:
            klc_begin_idx: 起始合并K线索引

        返回:
            原始K线单元的生成器迭代器

        Python 语法：yield from 是生成器委托，逐个产出嵌套列表中的元素
        Java 对比：类似于 Java 中两层 for 循环的扁平化迭代
        """
        for klc in self.lst[klc_begin_idx:]:
            yield from klc.lst


def cal_seg(bi_list, seg_list: CSegListComm, last_sure_seg_start_bi_idx):
    """
    计算线段并更新笔的线段归属

    参数:
        bi_list: 笔列表（或线段列表，用于线段线段计算）
        seg_list: 线段列表
        last_sure_seg_start_bi_idx: 最后一个确认线段的起始笔索引

    返回:
        更新后的最后一个确认线段起始笔索引

    处理逻辑：
    1. 更新线段列表（seg_list.update）
    2. 从后往前遍历所有笔，为每笔设置其所属的线段索引
    3. 找到最后一个确认的线段，返回其起始笔索引

    缠论知识 - 线段确认：
    线段由笔构成，但只有被后续线段破坏后，前面的线段才算"确认"。
    最后一个线段可能尚未确认（因为后面的笔可能继续延伸或破坏它）。
    """
    seg_list.update(bi_list)  # 更新线段列表

    if len(seg_list) == 0:
        # 没有线段：所有笔都标记为 seg_idx=0（不属于任何线段）
        for bi in bi_list:
            bi.set_seg_idx(0)
        return -1

    cur_seg: CSeg = seg_list[-1]  # 从最后一个线段开始

    # 从后往前遍历所有笔，为每笔设置所属线段索引
    bi_idx = len(bi_list) - 1
    while bi_idx >= 0:
        bi = bi_list[bi_idx]
        if bi.seg_idx is not None and bi.idx < last_sure_seg_start_bi_idx:
            break  # 已经确认过的笔，不再重复处理
        if bi.idx > cur_seg.end_bi.idx:
            # 笔在最后一个线段之后 → 标记为下一个线段
            bi.set_seg_idx(cur_seg.idx+1)
            bi_idx -= 1
            continue
        if bi.idx < cur_seg.start_bi.idx:
            # 笔在当前线段之前 → 前移到上一个线段
            assert cur_seg.pre
            cur_seg = cur_seg.pre
        bi.set_seg_idx(cur_seg.idx)
        bi_idx -= 1

    # 找到最后一个确认的线段起始笔索引
    last_sure_seg_start_bi_idx = -1
    seg = seg_list[-1]
    while seg:
        if seg.is_sure:
            last_sure_seg_start_bi_idx = seg.start_bi.idx
            break
        seg = seg.pre
    return last_sure_seg_start_bi_idx


def update_zs_in_seg(bi_list, seg_list, zs_list):
    """
    将中枢关联到对应的线段中

    参数:
        bi_list: 笔列表
        seg_list: 线段列表
        zs_list: 中枢列表

    处理逻辑：
    1. 从后往前遍历线段
    2. 对每个线段，找到所有位于其中的中枢
    3. 为每个中枢设置 bi_in（进入笔）、bi_out（离开笔）、bi_lst（构成笔列表）

    缠论知识 - 中枢与线段的关系：
    中枢由至少三笔重叠构成，每个中枢必定位于某个线段内部。
    中枢的 bi_in 是进入中枢的笔（中枢第一笔的前一笔），bi_out 是离开中枢的笔（中枢最后一笔的后一笔）。
    这两个笔用于判断中枢的第三类买卖点。

    缠论知识 - 线段内部元素的确认：
    当线段内部有超过2个确认中枢时，线段内部的笔和中枢就是"确认"的（ele_inside_is_sure=True）。
    这个标志用于后续的买卖点分析。
    """
    sure_seg_cnt = 0
    seg_idx = len(seg_list) - 1
    while seg_idx >= 0:
        seg = seg_list[seg_idx]
        if seg.ele_inside_is_sure:
            break  # 已经确认的线段，不再重复处理
        if seg.is_sure:
            sure_seg_cnt += 1
        seg.clear_zs_lst()  # 清空原有中枢列表，重新计算

        # 从后往前遍历中枢，找到属于当前线段的中枢
        _zs_idx = len(zs_list) - 1
        while _zs_idx >= 0:
            zs = zs_list[_zs_idx]
            if zs.end.idx < seg.start_bi.get_begin_klu().idx:
                break  # 中枢在线段开始之前，结束查找
            if zs.is_inside(seg):
                seg.add_zs(zs)  # 中枢在线段内部，加入线段的中枢列表
            # 设置中枢的 bi_in 和 bi_out
            assert zs.begin_bi.idx > 0
            zs.set_bi_in(bi_list[zs.begin_bi.idx-1])  # 进入笔：中枢第一笔的前一笔
            if zs.end_bi.idx+1 < len(bi_list):
                zs.set_bi_out(bi_list[zs.end_bi.idx+1])  # 离开笔：中枢最后一笔的后一笔
            zs.set_bi_lst(list(bi_list[zs.begin_bi.idx:zs.end_bi.idx+1]))  # 中枢包含的笔
            _zs_idx -= 1

        if sure_seg_cnt > 2:
            if not seg.ele_inside_is_sure:
                seg.ele_inside_is_sure = True  # 内部元素确认
        seg_idx -= 1