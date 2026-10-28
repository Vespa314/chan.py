# -*- coding: utf-8 -*-
"""
特征序列分形模块 - 缠论线段划分的核心算法（特征序列法）

Java 开发者注意：
- Python 的 ... (Ellipsis) 在代码中用作占位符，类似于 Java 的 // TODO
- Python 的 := (海象运算符) 在表达式内赋值，Java 没有直接对应
- Optional[T] 类似于 Java 的 @Nullable T
- Python 的列表推导式 [x for x in list if cond] 类似于 Java 的 Stream.filter().collect()
- Python 的 next(iter, default) 类似于 Java 的 stream.findFirst().orElse(default)
- Python 的 yield from 是生成器委托，类似于 Java 的 flatMap
- Python 的 id() 函数返回对象内存地址，类似于 Java 的 System.identityHashCode()

缠论知识 - 特征序列法（核心算法）：
特征序列法是缠论中最重要的线段划分方法。

基本概念：
- 上升线段中，所有下降笔构成特征序列（把下降笔当作K线看待）
- 下降线段中，所有上升笔构成特征序列（把上升笔当作K线看待）
- 在特征序列中找分型（顶分型/底分型），找到分型就确认了前面的线段

线段破坏的两种情况：
1. 第一种情况（无缺口）：特征序列分型的第一和第二元素之间没有跳空缺口
   → 分型形成即确认线段结束
2. 第二种情况（有缺口）：特征序列分型的第一和第二元素之间存在跳空缺口
   → 需要等待反向特征序列分型确认

算法流程：
1. 收集反向笔作为特征序列元素
2. 对特征序列元素进行包含处理（与K线包含处理完全相同）
3. 在特征序列中找分型（三元素：ele[0], ele[1], ele[2]）
4. 分型形成后，判断是否可以结束（can_be_end）
5. 如果确认结束，创建新线段
"""

from typing import List, Optional

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, FX_TYPE, KLINE_DIR, SEG_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import revert_bi_dir

from .Eigen import CEigen


class CEigenFX:
    """
    特征序列分形 - 管理特征序列的三个元素并检测分形

    这是整个缠论线段划分的核心。每个 CEigenFX 实例负责：
    1. 收集反向笔作为特征序列
    2. 对特征序列元素进行包含处理
    3. 检测三元素分形
    4. 判断线段是否可以结束

    属性说明：
    - dir: 线段方向（BI_DIR.UP 或 BI_DIR.DOWN）
    - ele: 三个特征序列元素 [ele0, ele1, ele2]
    - lst: 所有被收集的笔列表
    - exclude_included: 是否排除被包含的情况
    - kl_dir: 特征序列元素的方向（与线段方向相反）
    - last_evidence_bi: 最后一个证据笔（用于确认线段结束）
    - actual_break_flag: 是否实际突破（用于判断第二种情况）
    """

    def __init__(self, _dir: BI_DIR, exclude_included=True, lv=SEG_TYPE.BI):
        """
        初始化特征序列分形

        参数:
            _dir: 线段方向
            exclude_included: 是否排除被包含（默认 True，特征序列模式）
            lv: 线段层级

        注意：kl_dir 与线段方向相反
        - 上升线段（dir=UP）→ kl_dir=UP（特征序列向上找顶分型）
        - 下降线段（dir=DOWN）→ kl_dir=DOWN（特征序列向下找底分型）
        """
        self.lv = lv
        self.dir = _dir  # 线段方向
        self.ele: List[Optional[CEigen]] = [None, None, None]  # 三元素：ele[0], ele[1], ele[2]
        self.lst: List[CBi] = []  # 所有被收集的笔
        self.exclude_included = exclude_included
        self.kl_dir = KLINE_DIR.UP if _dir == BI_DIR.UP else KLINE_DIR.DOWN
        self.last_evidence_bi: Optional[CBi] = None  # 最后证据笔
        self.last_evidence_bi_is_sure: bool = False
        self.actual_break_flag = True  # 实际突破标志

    def treat_first_ele(self, bi: CBi) -> bool:
        """
        处理第一个特征序列元素

        参数:
            bi: 反向笔

        返回: False（第一元素不可能形成分形）

        逻辑：直接将第一笔作为第一元素，不做任何合并判断。
        """
        self.ele[0] = CEigen(bi, self.kl_dir)
        return False

    def treat_second_ele(self, bi: CBi) -> bool:
        """
        处理第二个特征序列元素

        参数:
            bi: 反向笔

        返回: True 如果需要重置，False 正常

        逻辑：
        1. 尝试将 bi 合并到第一元素中
        2. 如果无法合并，创建第二元素
        3. 如果前两元素不可能形成分形（第二元素弱于第一元素），重置

        缠论知识 - 前两元素不可能成为分形：
        - 上升线段（找顶分型）：第二元素高点 < 第一元素高点 → 不可能
        - 下降线段（找底分型）：第二元素低点 > 第一元素低点 → 不可能
        """
        assert self.ele[0] is not None
        combine_dir = self.ele[0].try_add(bi, exclude_included=self.exclude_included)
        if combine_dir != KLINE_DIR.COMBINE:  # 不能合并
            self.ele[1] = CEigen(bi, self.kl_dir)
            if (self.is_up() and self.ele[1].high < self.ele[0].high) or \
               (self.is_down() and self.ele[1].low > self.ele[0].low):
                return self.reset()  # 前两元素不可能成为分形，重置
        return False

    def treat_third_ele(self, bi: CBi) -> bool:
        """
        处理第三个特征序列元素（检测分形）

        参数:
            bi: 反向笔

        返回: True 如果形成分形，False 如果未形成

        逻辑：
        1. 尝试将 bi 合并到第二元素中
        2. 如果无法合并，创建第三元素
        3. 检查是否实际突破（actual_break）
        4. 如果形成分形，调用 update_fx 检测分型类型
        5. 判断分型是否与线段方向一致

        缠论知识 - 分形判断：
        - 上升线段（dir=UP）：特征序列找顶分型（FX_TYPE.TOP）
        - 下降线段（dir=DOWN）：特征序列找底分型（FX_TYPE.BOTTOM）

        allow_top_equal 的处理：
        - 反向笔是下降笔（bi.is_down()）：allow_top_equal=1（顶部相等不合并）
        - 反向笔是上升笔（bi.is_up()）：allow_top_equal=-1（底部相等不合并）
        """
        assert self.ele[0] is not None
        assert self.ele[1] is not None
        self.last_evidence_bi = bi
        self.last_evidence_bi_is_sure = bi.is_used_to_be_sure
        allow_top_equal = (1 if bi.is_down() else -1) if self.exclude_included else None
        combine_dir = self.ele[1].try_add(bi, allow_top_equal=allow_top_equal)
        if combine_dir == KLINE_DIR.COMBINE:
            return False  # 被合并到第二元素，继续等待
        self.ele[2] = CEigen(bi, combine_dir)
        if not self.actual_break():
            return self.reset()  # 没有实际突破，重置
        # 检测分型（update_fx 会设置 ele[1].fx）
        self.ele[1].update_fx(self.ele[0], self.ele[2], exclude_included=self.exclude_included, allow_top_equal=allow_top_equal)
        fx = self.ele[1].fx
        is_fx = (self.is_up() and fx == FX_TYPE.TOP) or (self.is_down() and fx == FX_TYPE.BOTTOM)
        return True if is_fx else self.reset()

    def add(self, bi: CBi) -> bool:
        """
        添加一笔到特征序列，返回是否形成分形

        参数:
            bi: 与线段方向相反的笔

        返回:
            True: 形成了分形，线段可以确认
            False: 尚未形成分形，继续等待

        这是特征序列法的核心入口方法。
        根据当前元素数量，分派到 treat_first_ele / treat_second_ele / treat_third_ele。

        注意：assert bi.dir != self.dir 确保只添加反向笔。
        """
        assert bi.dir != self.dir
        self.lst.append(bi)
        if self.ele[0] is None:  # 第一元素
            return self.treat_first_ele(bi)
        elif self.ele[1] is None:  # 第二元素
            return self.treat_second_ele(bi)
        elif self.ele[2] is None:  # 第三元素
            return self.treat_third_ele(bi)
        else:
            raise CChanException(f"特征序列3个都找齐了还没处理!! 当前笔:{bi.idx},当前:{str(self)}", ErrCode.SEG_EIGEN_ERR)

    def reset(self):
        """
        重置特征序列，从第二笔开始重新构建

        返回:
            True 如果重置后形成了新的分形

        两种重置模式：
        1. exclude_included=True（特征序列模式）：
           完全清空，从 lst[1:] 开始重新构建
        2. exclude_included=False（普通模式）：
           将第二元素移到第一位，第三元素移到第二位，从第三元素开始继续

        缠论知识 - 特征序列重置：
        当三元素没有形成分形时，需要"滑动窗口"：去掉第一元素，
        将第二元素作为新的第一元素，继续收集后续元素。
        这类似于在K线合并中，合并后的K线继续与下一根K线比较。
        """
        bi_tmp_list = list(self.lst[1:])  # 去掉第一笔
        if self.exclude_included:
            # 完全清空，重新构建
            self.clear()
            for bi in bi_tmp_list:
                if self.add(bi):
                    return True
        else:
            # 滑动窗口：ele[1] → ele[0], ele[2] → ele[1], ele[2] → None
            assert self.ele[1] is not None
            ele2_begin_idx = self.ele[1].lst[0].idx
            self.ele[0], self.ele[1], self.ele[2] = self.ele[1], self.ele[2], None
            # Python 语法：多重赋值，同时交换三个变量的值
            # Java 对比：需要临时变量逐个交换
            self.lst = [bi for bi in bi_tmp_list if bi.idx >= ele2_begin_idx]

        return False

    def can_be_end(self, bi_lst: CBiList):
        """
        判断特征序列分形是否可以结束线段

        参数:
            bi_lst: 笔列表

        返回:
            True: 线段可以结束（第一种情况：无缺口确认）
            None: 线段可能结束但需要更多确认（第二种情况：有缺口）
            False: 线段不能结束

        缠论知识 - 线段结束判断：
        1. 无缺口（ele[1].gap=False）：
           如果 actual_break_flag=True，直接返回 True（第一种情况）
           如果 actual_break_flag=False，返回 None（等待确认）
        2. 有缺口（ele[1].gap=True）：
           需要等待反向特征序列分型确认（第二种情况）
           调用 find_revert_fx 查找反向特征序列

        第二种情况的处理：
        当特征序列分型的第一和第二元素间有跳空缺口时，
        需要找反向特征序列分型来确认线段的结束。
        如果反向分型也找到了，线段才真正结束。
        """
        assert self.ele[1] is not None
        if self.ele[1].gap:
            # 有缺口 → 第二种情况：需要反向特征序列确认
            assert self.ele[0] is not None
            end_bi_idx = self.GetPeakBiIdx()
            thred_value = bi_lst[end_bi_idx].get_end_val()
            break_thred = self.ele[0].low if self.is_up() else self.ele[0].high
            return self.find_revert_fx(bi_lst, end_bi_idx+2, thred_value, break_thred)
        else:
            # 无缺口 → 第一种情况：直接确认
            if not self.actual_break_flag:
                return None  # 没有实际突破，等待确认
            return True

    def is_down(self):
        return self.dir == BI_DIR.DOWN

    def is_up(self):
        return self.dir == BI_DIR.UP

    def GetPeakBiIdx(self):
        """获取特征序列分形对应的极值笔索引"""
        assert self.ele[1] is not None
        return self.ele[1].GetPeakBiIdx()

    def all_bi_is_sure(self):
        """
        检查特征序列中的所有笔是否都是确认的

        Python 语法：next(iter, default) 获取迭代器第一个元素，指定默认值
        Java 对比：stream.findFirst().orElse(default)
        """
        assert self.last_evidence_bi is not None
        return next((False for bi in self.lst if not bi.is_used_to_be_sure), True) and self.last_evidence_bi_is_sure

    def clear(self):
        """清空所有元素"""
        self.ele = [None, None, None]
        self.lst = []

    def __str__(self):
        """字符串表示，格式如 '0,1,2 | 3,4 | 5,6,7'"""
        _t = [f"{[] if ele is None else ','.join([str(b.idx) for b in ele.lst])}" for ele in self.ele]
        return " | ".join(_t)

    def actual_break(self):
        """
        判断第三元素是否实际突破了第二元素的端点

        返回:
            True: 实际突破，分形有效
            False: 没有实际突破

        缠论知识 - 实际突破：
        特征序列的第三元素必须实际突破第二元素的端点，
        否则分形不成立。这是为了防止"假分形"。

        判断逻辑：
        1. 如果 exclude_included=False（普通模式），直接返回 True
        2. 如果第三元素直接突破了第二元素中最后一笔的端点 → True
        3. 如果第三元素只有一笔，检查后续笔是否突破：
           - 如果后续笔突破了 → True
           - 如果后续笔未确认且没有更多笔 → actual_break_flag=False，返回 True
           - 如果后续笔已确认或没有后续笔 → 继续检查
        4. 如果第三元素只有一笔且没有后续 → actual_break_flag=False

        actual_break_flag 的作用：
        当设为 False 时，can_be_end 会返回 None 而不是 True，
        这意味着即使分形形成，线段也不会立即确认，需要等待更多数据。
        """
        if not self.exclude_included:
            return True
        assert self.ele[2] and self.ele[1]
        # 直接突破：第三元素端点直接突破了第二元素最后一笔的端点
        if (self.is_up() and self.ele[2].low < self.ele[1][-1]._low()) or \
           (self.is_down() and self.ele[2].high > self.ele[1][-1]._high()):
            return True

        # 第三元素只有一笔，需要检查后续笔
        assert len(self.ele[2]) == 1
        ele2_bi = self.ele[2][0]
        if ele2_bi.next and ele2_bi.next.next:
            # 后面还有至少两笔
            if ele2_bi.is_down():
                if ele2_bi.next.next._low() < ele2_bi._low():
                    # 后续笔突破了第三元素端点
                    self.last_evidence_bi = ele2_bi.next.next
                    self.last_evidence_bi_is_sure = ele2_bi.next.next.is_used_to_be_sure
                    return True
                else:
                    if not ele2_bi.next.next.is_used_to_be_sure or ele2_bi.next.next.next is None:
                        self.actual_break_flag = False
                        return True
            elif ele2_bi.is_up():
                if ele2_bi.next.next._high() > ele2_bi._high():
                    self.last_evidence_bi = ele2_bi.next.next
                    self.last_evidence_bi_is_sure = ele2_bi.next.next.is_used_to_be_sure
                    return True
                else:
                    if not ele2_bi.next.next.is_used_to_be_sure or ele2_bi.next.next.next is None:
                        self.actual_break_flag = False
                        return True
        else:
            if ele2_bi.next:
                if self.is_up() and ele2_bi.next._high() > self.ele[1].high:
                    ...
                elif self.is_down() and ele2_bi.next._low() < self.ele[1].low:
                    ...
                else:
                    self.actual_break_flag = False
                    return True
            else:
                self.actual_break_flag = False
                return True
        return False

    def find_revert_fx(self, bi_list: CBiList, begin_idx: int, thred_value: float, break_thred: float):
        """
        查找反向特征序列分形（第二种情况的处理）

        参数:
            bi_list: 笔列表
            begin_idx: 开始查找的笔索引
            thred_value: 阈值（线段的端点值）
            break_thred: 突破阈值（第一元素的极值）

        返回:
            True: 找到反向分形，线段确认结束
            None: 找到末尾仍未找到反向分形
            False: 被重置

        缠论知识 - 第二种情况的确认：
        当特征序列分形有缺口时，需要等待反向特征序列形成分形。
        这里的反向特征序列方向与原特征序列相反。

        例如：
        - 上升线段 → 特征序列是下降笔 → 找到顶分型有缺口
          → 需要找反向特征序列（上升笔）的底分型来确认

        找反向分形的逻辑：
        1. 从 begin_idx 开始，每隔一笔取一笔（取同向笔）
        2. 创建反向特征序列（CEigenFX）
        3. 如果找到反向分形，检查是否可以结束
        4. 如果反向分形可以结束，线段确认
        5. 如果反向分形被重置，继续找下一个
        """
        COMMON_COMBINE = False  # 是否用普通分形合并规则处理
        first_bi_dir = bi_list[begin_idx].dir  # 第一笔的方向
        # 创建反向特征序列：方向与第一笔方向相反
        egien_fx = CEigenFX(revert_bi_dir(first_bi_dir), exclude_included=not COMMON_COMBINE, lv=self.lv)

        # 每隔一笔取一笔（同向笔），跳过反向笔
        for bi in bi_list[begin_idx::2]:  # Python 语法：切片步长，begin_idx 开始每2步取一个
            if egien_fx.add(bi):
                if COMMON_COMBINE:
                    return True

                while True:
                    _test = egien_fx.can_be_end(bi_list)
                    if not egien_fx.actual_break_flag:
                        _test = None
                    if _test in [True, None]:
                        assert egien_fx.ele[2]
                        self.last_evidence_bi = egien_fx.ele[2].lst[-1]
                        if _test is True:
                            self.last_evidence_bi_is_sure = self.last_evidence_bi.is_used_to_be_sure and egien_fx.last_evidence_bi_is_sure
                        return _test
                    elif not egien_fx.reset():
                        break  # 重置失败，跳出 while 继续外层 for

        return None  # 找到末尾也没有找到反向分形