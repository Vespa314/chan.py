# -*- coding: utf-8 -*-
"""
线段列表公共基类 - 定义线段管理的通用逻辑

Java 开发者注意：
- abc.abstractmethod 是 Python 的抽象方法装饰器，类似于 Java 的 abstract 关键字
  Java 对比：abstract void update(CBiList bi_lst);
- Generic[SUB_LINE_TYPE] 是 Python 泛型，类似于 Java 的 <SUB_LINE_TYPE>
- yield from 是生成器委托，类似于 Java 的 Stream.flatMap()
- Python 的 := (海象运算符) 在表达式中赋值，类似于 Java 中先赋值再判断
  Java 对比：没有直接对应，需要分开写
- TypeVar 支持约束语法 TypeVar('T', A, B)，类似于 Java 的 <T extends A | B>
"""

import abc
from typing import Generic, List, TypeVar, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, LEFT_SEG_METHOD, SEG_TYPE
from Common.ChanException import CChanException, ErrCode

from .Seg import CSeg
from .SegConfig import CSegConfig

SUB_LINE_TYPE = TypeVar('SUB_LINE_TYPE', CBi, "CSeg")
# 泛型类型变量，约束为 CBi 或 CSeg
# Java 对比：<T extends CBi | CSeg>（但 Java 泛型不支持联合类型）


class CSegListComm(Generic[SUB_LINE_TYPE]):
    """
    线段列表公共基类 - 定义线段列表的通用接口和逻辑

    这是所有线段算法的基类，定义了：
    - 线段列表的增删改查
    - 尾部未确认线段的收集逻辑
    - 首段线段的特殊处理

    泛型参数 SUB_LINE_TYPE：
    - 当 lv=SEG_TYPE.BI：SUB_LINE_TYPE = CBi（笔的线段）
    - 当 lv=SEG_TYPE.SEG：SUB_LINE_TYPE = CSeg[CBi]（线段的线段）

    属性说明：
    - lst: 线段列表
    - lv: 线段层级（BI 或 SEG）
    - config: 线段配置
    """

    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        self.lst: List[CSeg[SUB_LINE_TYPE]] = []
        self.lv = lv
        self.do_init()
        self.config = seg_config

    def do_init(self):
        """重置线段列表"""
        self.lst = []

    def __iter__(self):
        """支持 for...in 循环"""
        yield from self.lst

    @overload
    def __getitem__(self, index: int) -> CSeg[SUB_LINE_TYPE]: ...

    @overload
    def __getitem__(self, index: slice) -> List[CSeg[SUB_LINE_TYPE]]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CSeg[SUB_LINE_TYPE]], CSeg[SUB_LINE_TYPE]]:
        """支持 [] 索引访问"""
        return self.lst[index]

    def __len__(self):
        return len(self.lst)

    def left_bi_break(self, bi_lst: CBiList):
        """
        检查最后一个确认线段之后的笔是否突破了该线段的端点

        返回:
            True 如果有笔突破了最后一个线段的端点

        缠论知识 - 线段破坏：
        线段被破坏的标志是后续笔突破了线段的端点。
        如果向上线段的端点被后续笔的高点突破，说明线段可能被破坏。
        """
        if len(self) == 0:
            return False
        last_seg_end_bi = self[-1].end_bi
        for bi in bi_lst[last_seg_end_bi.idx+1:]:
            if last_seg_end_bi.is_up() and bi._high() > last_seg_end_bi._high():
                return True
            elif last_seg_end_bi.is_down() and bi._low() < last_seg_end_bi._low():
                return True
        return False

    def collect_first_seg(self, bi_lst: CBiList):
        """
        收集第一条线段（特殊处理，因为之前没有参考线段）

        参数:
            bi_lst: 笔列表

        两种处理方式：
        1. PEAK 模式：找极值点作为第一条线段
           - 比较最高点和最低点偏离起始点的幅度
           - 选择偏离幅度更大的方向
        2. ALL 模式：把所有笔收集为一条线段
           - 方向由整体走势决定

        缠论知识 - 第一条线段：
        第一条线段的确定比较特殊，因为没有前面的线段作为参考。
        通常用极值法或整体走势法来确定方向。
        """
        if len(bi_lst) < 3:
            return
        if self.config.left_method == LEFT_SEG_METHOD.PEAK:
            # 找极值点作为第一条线段
            _high = max(bi._high() for bi in bi_lst)
            _low = min(bi._low() for bi in bi_lst)
            if abs(_high-bi_lst[0].get_begin_val()) >= abs(_low-bi_lst[0].get_begin_val()):
                # 高点偏离更多 → 上升线段
                peak_bi = FindPeakBi(bi_lst, is_high=True)
                assert peak_bi is not None
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, split_first_seg=False, reason="0seg_find_high")
            else:
                # 低点偏离更多 → 下降线段
                peak_bi = FindPeakBi(bi_lst, is_high=False)
                assert peak_bi is not None
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, split_first_seg=False, reason="0seg_find_low")
            self.collect_left_as_seg(bi_lst)
        elif self.config.left_method == LEFT_SEG_METHOD.ALL:
            _dir = BI_DIR.UP if bi_lst[-1].get_end_val() >= bi_lst[0].get_begin_val() else BI_DIR.DOWN
            self.add_new_seg(bi_lst, bi_lst[-1].idx, is_sure=False, seg_dir=_dir, split_first_seg=False, reason="0seg_collect_all")
        else:
            raise CChanException(f"unknown seg left_method = {self.config.left_method}", ErrCode.PARA_ERROR)

    def collect_left_seg_peak_method(self, last_seg_end_bi, bi_lst):
        """
        PEAK 模式下的尾部线段收集（递归）

        参数:
            last_seg_end_bi: 最后一个确认线段的结束笔
            bi_lst: 笔列表

        递归逻辑：
        1. 根据最后一个线段的方向，找剩余的极值笔
        2. 如果找到且距离 >= 3笔，创建新线段
        3. 递归处理剩余部分
        4. 如果找不到，用 collect_left_as_seg 收集剩余
        """
        find_new_seg = False
        if last_seg_end_bi.is_down():
            # 上一个线段是下降的 → 找高点作为新线段
            peak_bi = FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=True)
            if peak_bi and peak_bi.idx - last_seg_end_bi.idx >= 3:
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, reason="collectleft_find_high")
                find_new_seg = True
        else:
            # 上一个线段是上升的 → 找低点作为新线段
            peak_bi = FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=False)
            if peak_bi and peak_bi.idx - last_seg_end_bi.idx >= 3:
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, reason="collectleft_find_low")
                find_new_seg = True
        last_seg_end_bi = self[-1].end_bi
        if not find_new_seg:
            self.collect_left_as_seg(bi_lst)
        else:
            self.collect_left_seg_peak_method(last_seg_end_bi, bi_lst)  # 递归处理剩余

    def collect_segs(self, bi_lst):
        """
        收集尾部未确认的线段

        参数:
            bi_lst: 笔列表

        分段处理逻辑：
        1. 如果剩余笔数 < 3，不处理
        2. 如果剩余笔突破了最后一个线段的端点 → 强制收集
        3. 如果剩余笔与最后一个线段同向 → 根据 left_method 处理
        4. 如果剩余笔与最后一个线段反向 → 根据 left_method 处理
        """
        last_bi = bi_lst[-1]
        last_seg_end_bi = self[-1].end_bi
        if last_bi.idx-last_seg_end_bi.idx < 3:
            return

        if last_seg_end_bi.is_down() and last_bi.get_end_val() <= last_seg_end_bi.get_end_val():
            # 下降线段后，剩余笔的结束值更低 → 线段延伸
            if peak_bi := FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=True):
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, reason="collectleft_find_high_force")
                self.collect_left_seg(bi_lst)
        elif last_seg_end_bi.is_up() and last_bi.get_end_val() >= last_seg_end_bi.get_end_val():
            # 上升线段后，剩余笔的结束值更高 → 线段延伸
            if peak_bi := FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=False):
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, reason="collectleft_find_low_force")
                self.collect_left_seg(bi_lst)
        elif self.config.left_method == LEFT_SEG_METHOD.ALL:
            # 与最后一个线段反向，ALL 模式：全部收集
            self.collect_left_as_seg(bi_lst)
        elif self.config.left_method == LEFT_SEG_METHOD.PEAK:
            # 与最后一个线段反向，PEAK 模式：递归找极值
            self.collect_left_seg_peak_method(last_seg_end_bi, bi_lst)
        else:
            raise CChanException(f"unknown seg left_method = {self.config.left_method}", ErrCode.PARA_ERROR)

    def collect_left_seg(self, bi_lst: CBiList):
        """
        收集尾部线段的总入口

        逻辑：
        1. 如果没有线段 → 收集第一条线段
        2. 如果有线段 → 收集后续线段
        3. 如果收集后尾部仍有超过2笔未处理，且最后一个线段不确定 → 重新收集
        """
        if len(self) == 0:
            self.collect_first_seg(bi_lst)
        else:
            self.collect_segs(bi_lst)
            if len(bi_lst) > 0 and len(self.lst) > 0 and bi_lst[-1].idx - self.lst[-1].bi_list[-1].idx > 2 and not self.lst[-1].is_sure:
                self.lst = self.lst[:-1]  # 移除最后一个不确定线段
                self.collect_left_seg(bi_lst)  # 递归重新收集

    def collect_left_as_seg(self, bi_lst: CBiList):
        """
        把所有剩余笔收集为一个线段

        参数:
            bi_lst: 笔列表

        逻辑：
        - 如果最后一笔与最后一个线段同向 → 使用倒数第二笔作为结束
        - 如果最后一笔与最后一个线段反向 → 使用最后一笔作为结束
        """
        last_bi = bi_lst[-1]
        last_seg_end_bi = self[-1].end_bi
        if last_seg_end_bi.idx+1 >= len(bi_lst):
            return
        if last_seg_end_bi.dir == last_bi.dir:
            self.add_new_seg(bi_lst, last_bi.idx-1, is_sure=False, reason="collect_left_1")
        else:
            self.add_new_seg(bi_lst, last_bi.idx, is_sure=False, reason="collect_left_0")

    def try_add_new_seg(self, bi_lst, end_bi_idx: int, is_sure=True, seg_dir=None, split_first_seg=True, reason="normal"):
        """
        尝试添加新线段

        参数:
            bi_lst: 笔列表
            end_bi_idx: 结束笔索引
            is_sure: 是否确认
            seg_dir: 线段方向
            split_first_seg: 是否分割第一条线段
            reason: 创建原因

        特殊逻辑 - 第一条线段分割（split_first_seg）：
        如果第一条线段 >= 3笔，尝试从中间分割：
        找到反向极值笔，将第一条线段拆分为两段。
        这样可以避免第一条线段过长。
        """
        if len(self) == 0 and split_first_seg and end_bi_idx >= 3:
            # 尝试分割第一条线段
            if peak_bi := FindPeakBi(bi_lst[end_bi_idx-3::-1], bi_lst[end_bi_idx].is_down()):
                if (peak_bi.is_down() and (peak_bi._low() < bi_lst[0]._low() or peak_bi.idx == 0)) or \
                   (peak_bi.is_up() and (peak_bi._high() > bi_lst[0]._high() or peak_bi.idx == 0)):
                    # 极值笔比第一笔开头还极端（因为没有比较到），可以分割
                    self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=peak_bi.dir, reason="split_first_1st")
                    self.add_new_seg(bi_lst, end_bi_idx, is_sure=False, reason="split_first_2nd")
                    return

        # 确定起始笔
        bi1_idx = 0 if len(self) == 0 else self[-1].end_bi.idx+1
        bi1 = bi_lst[bi1_idx]
        bi2 = bi_lst[end_bi_idx]
        self.lst.append(CSeg(len(self.lst), bi1, bi2, is_sure=is_sure, seg_dir=seg_dir, reason=reason))

        if len(self.lst) >= 2:
            self.lst[-2].next = self.lst[-1]
            self.lst[-1].pre = self.lst[-2]
        self.lst[-1].update_bi_list(bi_lst, bi1_idx, end_bi_idx)

    def add_new_seg(self, bi_lst: CBiList, end_bi_idx: int, is_sure=True, seg_dir=None, split_first_seg=True, reason="normal"):
        """
        添加新线段（带异常处理）

        异常处理：
        - 如果第一条线段的值校验失败（SEG_END_VALUE_ERR），跳过并继续
        - 其他异常正常抛出
        """
        try:
            self.try_add_new_seg(bi_lst, end_bi_idx, is_sure, seg_dir, split_first_seg, reason)
        except CChanException as e:
            if e.errcode == ErrCode.SEG_END_VALUE_ERR and len(self.lst) == 0:
                return False
            raise e
        except Exception as e:
            raise e
        return True

    @abc.abstractmethod
    def update(self, bi_lst: CBiList):
        """
        更新线段列表（抽象方法）

        子类必须实现此方法，定义具体的线段更新算法。
        这是模板方法模式的核心。

        Python 特性：@abc.abstractmethod 要求子类必须实现
        Java 对比：abstract void update(CBiList bi_lst);
        """
        ...

    def exist_sure_seg(self):
        """
        是否存在确认的线段

        Python 语法：any(condition for item in iterable)
        Java 对比：list.stream().anyMatch(seg -> seg.is_sure)
        """
        return any(seg.is_sure for seg in self.lst)


def FindPeakBi(bi_lst: Union[CBiList, List[CBi]], is_high):
    """
    在笔列表中查找极值笔

    参数:
        bi_lst: 笔列表
        is_high: True=找最高点，False=找最低点

    返回:
        极值笔，如果没有找到则返回 None

    查找逻辑：
    - 找高点：遍历所有上升笔，找到结束值最高的
    - 找低点：遍历所有下降笔，找到结束值最低的
    - 跳过"假突破"：如果前前笔的结束值比当前笔更极端，跳过当前笔
    """
    peak_val = float("-inf") if is_high else float("inf")
    peak_bi = None
    for bi in bi_lst:
        if (is_high and bi.get_end_val() >= peak_val and bi.is_up()) or \
           (not is_high and bi.get_end_val() <= peak_val and bi.is_down()):
            # 跳过假突破：如果前前笔更极端，说明当前笔不是真正的极值
            if bi.pre and bi.pre.pre and \
               ((is_high and bi.pre.pre.get_end_val() > bi.get_end_val()) or
                (not is_high and bi.pre.pre.get_end_val() < bi.get_end_val())):
                continue
            peak_val = bi.get_end_val()
            peak_bi = bi
    return peak_bi