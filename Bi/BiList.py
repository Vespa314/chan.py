# -*- coding: utf-8 -*-
"""
笔列表模块 - 管理笔的创建、更新、删除和验证

Java 开发者注意：
- yield from 是 Python 生成器委托，产出迭代器中的每个元素
  Java 对比：类似于 Iterator 的 flatMap 或 Stream.flatMap()
- @overload 仅用于类型提示，不影响运行时行为
  Java 对比：Java 直接写多个重载方法
- Python 的 del 关键字删除列表元素，类似于 Java 的 list.remove(index)
- Python 的函数内可以定义嵌套函数（如 try_update_end 中的 check_top/check_bottom）
  Java 对比：Java 不支持函数内定义函数，通常用 Lambda 或内部类
"""

from typing import List, Optional, Union, overload

from Common.CEnum import FX_TYPE, KLINE_DIR
from KLine.KLine import CKLine

from .Bi import CBi
from .BiConfig import CBiConfig


class CBiList:
    """
    笔列表 - 管理某一级别下所有笔的集合

    这是笔计算的核心模块，处理：
    1. 新笔的创建（分型确认后）
    2. 笔的延伸（同一方向继续更新）
    3. 笔的破坏（反向分型形成新笔）
    4. 虚拟笔管理（最后一笔未确认时的处理）
    5. 笔的峰值更新（次高点/次低点处理）

    缠论知识 - 笔的确认过程：
    当出现反向分型且满足笔的K线数量条件时，前面的笔被确认。
    最后一笔可能是虚拟笔（未确认），等待后续K线确认或破坏。

    属性说明：
    - bi_list: 笔列表
    - last_end: 最后一笔的结束K线
    - config: 笔配置
    - free_klc_lst: 未形成笔前的分型K线缓存
    """

    def __init__(self, bi_conf=CBiConfig()):
        """
        初始化笔列表
        Python 注意：默认参数 bi_conf=CBiConfig() 在模块加载时计算一次，
        所有不传参数创建的 CBiList 共享同一个配置对象
        """
        self.bi_list: List[CBi] = []
        self.last_end = None  # 最后一笔的结束K线
        self.config = bi_conf

        self.free_klc_lst = []  # 第一笔未形成前，缓存分型K线。为获得更精准结果，不加对后续计算影响不大

    def __str__(self):
        """字符串表示，每笔一行"""
        return "\n".join([str(bi) for bi in self.bi_list])

    def __iter__(self):
        """支持 for...in 循环"""
        yield from self.bi_list

    @overload
    def __getitem__(self, index: int) -> CBi: ...

    @overload
    def __getitem__(self, index: slice) -> List[CBi]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CBi], CBi]:
        """支持 [] 索引访问"""
        return self.bi_list[index]

    def __len__(self):
        """支持 len() 函数"""
        return len(self.bi_list)

    def try_create_first_bi(self, klc: CKLine) -> bool:
        """
        尝试创建第一笔

        参数:
            klc: 当前分型K线

        返回:
            True 如果成功创建第一笔

        逻辑：
        第一笔比较特殊，因为之前没有确定的分型。
        需要缓存之前的K线，直到找到反向分型且满足笔的条件。

        缠论知识：第一笔的形成需要两个相反的分型且满足K线数量要求
        """
        for exist_free_klc in self.free_klc_lst:
            if exist_free_klc.fx == klc.fx:
                continue  # 同向分型，跳过
            if self.can_make_bi(klc, exist_free_klc):
                self.add_new_bi(exist_free_klc, klc)
                self.last_end = klc
                return True
        self.free_klc_lst.append(klc)  # 缓存，等待下一个分型
        self.last_end = klc
        return False

    def update_bi(self, klc: CKLine, last_klc: CKLine, cal_virtual: bool) -> bool:
        """
        更新笔列表（核心入口方法）

        参数:
            klc: 倒数第二根合并K线（新检测到的分型）
            last_klc: 倒数第一根合并K线（最新K线）
            cal_virtual: 是否计算虚拟笔

        返回:
            True 如果笔列表有变化

        执行两个步骤：
        1. update_bi_sure: 尝试确认前面的笔
        2. try_add_virtual_bi: 尝试添加虚拟笔（如果 cal_virtual=True）
        """
        flag1 = self.update_bi_sure(klc)
        if cal_virtual:
            flag2 = self.try_add_virtual_bi(last_klc)
            return flag1 or flag2
        else:
            return flag1

    def can_update_peak(self, klc: CKLine):
        """
        判断是否可以更新笔的端点（次高点/次低点优化）

        参数:
            klc: 新的候选端点K线

        返回:
            True 如果可以用 klc 替换当前笔的端点

        缠论知识 - 次高点/次低点：
        当笔的端点不是最高/最低点时，可以尝试用次高点/次低点替换，
        前提是满足以下条件：
        1. 允许次高点/次低点（bi_allow_sub_peak=True）
        2. 笔数量 >= 2
        3. 新的端点不会让笔的方向反转
        4. 新的端点满足极值条件
        5. 不会导致前后笔重叠
        """
        if self.config.bi_allow_sub_peak or len(self.bi_list) < 2:
            return False
        if self.bi_list[-1].is_down() and klc.high < self.bi_list[-1].get_begin_val():
            return False
        if self.bi_list[-1].is_up() and klc.low > self.bi_list[-1].get_begin_val():
            return False
        if not end_is_peak(self.bi_list[-2].begin_klc, klc):
            return False
        if self[-1].is_down() and self[-1].get_end_val() < self[-2].get_begin_val():
            return False
        if self[-1].is_up() and self[-1].get_end_val() > self[-2].get_begin_val():
            return False
        return True

    def update_peak(self, klc: CKLine, for_virtual=False):
        """
        更新最后一笔的端点（次高点/次低点替换）

        参数:
            klc: 新的候选端点K线
            for_virtual: 是否为虚拟笔

        返回:
            True 如果成功更新

        逻辑：
        1. 弹出最后一笔
        2. 尝试用新的端点更新
        3. 如果失败，恢复原笔
        """
        if not self.can_update_peak(klc):
            return False
        _tmp_last_bi = self.bi_list[-1]  # 保存原笔
        self.bi_list.pop()  # 弹出原笔
        if not self.try_update_end(klc, for_virtual=for_virtual):
            self.bi_list.append(_tmp_last_bi)  # 恢复原笔
            return False
        else:
            if for_virtual:
                self.bi_list[-1].append_sure_end(_tmp_last_bi.end_klc)
            return True

    def update_bi_sure(self, klc: CKLine) -> bool:
        """
        处理确认笔的逻辑

        参数:
            klc: 倒数第二根合并K线（新检测到的分型）

        返回:
            True 如果笔列表有变化

        处理流程：
        1. 删除虚拟笔
        2. 如果 klc 不是分型 → 检查虚拟笔是否变化
        3. 如果还没有笔 → 尝试创建第一笔
        4. 如果与 last_end 同向 → 尝试更新当前笔的端点
        5. 如果与 last_end 反向 → 检查是否可以形成新笔
        6. 如果以上都不满足 → 尝试更新峰值
        """
        _tmp_end = self.get_last_klu_of_last_bi()
        self.delete_virtual_bi()  # 先删除虚拟笔，重新判断

        if klc.fx == FX_TYPE.UNKNOWN:
            return _tmp_end != self.get_last_klu_of_last_bi()  # 虚笔是否有变

        if self.last_end is None or len(self.bi_list) == 0: # 还没有任何笔 → 尝试创建第一笔
            return self.try_create_first_bi(klc)

        if klc.fx == self.last_end.fx:
            # 同向分型：尝试延伸当前笔的结束点
            return self.try_update_end(klc)
        elif self.can_make_bi(klc, self.last_end):
            # 反向分型 + 满足笔的条件（满足 ≥4（严格模式）） → 创建新笔！
            self.add_new_bi(self.last_end, klc)
            self.last_end = klc
            return True
        elif self.update_peak(klc):
            # 反向分型但不满足条件 → 尝试次高点/次低点替换
            return True
        return _tmp_end != self.get_last_klu_of_last_bi()

    def delete_virtual_bi(self):
        """
        删除虚拟笔，将之前的确认状态恢复

        逻辑：
        1. 如果最后一笔是虚拟笔（未确认）
           - 如果有历史确认结束点：恢复到第一个确认结束点，后续的确认结束点作为新笔添加
           - 如果没有历史确认结束点：直接删除虚拟笔
        2. 更新 last_end 为最后一笔的结束K线
        """
        if len(self) > 0 and not self.bi_list[-1].is_sure:
            sure_end_list = [klc for klc in self.bi_list[-1].sure_end]
            if len(sure_end_list):
                # 有历史确认点：恢复到第一个确认点
                self.bi_list[-1].restore_from_virtual_end(sure_end_list[0])
                self.last_end = self[-1].end_klc
                # 后续的确认点作为新的确定笔
                for sure_end in sure_end_list[1:]:
                    self.add_new_bi(self.last_end, sure_end, is_sure=True)
                    self.last_end = self[-1].end_klc
            else:
                del self.bi_list[-1]  # 没有历史确认点，直接删除
        self.last_end = self[-1].end_klc if len(self) > 0 else None
        if len(self) > 0:
            self[-1].next = None

    def try_add_virtual_bi(self, klc: CKLine, need_del_end=False):
        """
        尝试添加或更新虚拟笔

        参数:
            klc: 最新的合并K线
            need_del_end: 是否需要先删除虚拟笔

        返回:
            True 如果虚拟笔有变化

        缠论知识 - 虚拟笔：
        在实时分析中，最后一笔可能尚未被反向分型确认。
        如果行情继续朝同一方向延伸，需要更新虚拟笔的结束点。

        逻辑：
        1. 如果 klc 方向与最后一笔一致且超过端点 → 更新虚拟笔结束点
        2. 如果 klc 方向与最后一笔相反 → 尝试创建新虚拟笔
        3. 从 klc 往前查找，看是否有能形成虚拟笔的分型
        """
        if need_del_end:
            self.delete_virtual_bi()
        if len(self) == 0:
            return False
        if klc.idx == self[-1].end_klc.idx:
            return False

        # 同向延伸：价格继续朝笔的方向发展
        if (self[-1].is_up() and klc.high >= self[-1].end_klc.high) or \
           (self[-1].is_down() and klc.low <= self[-1].end_klc.low):
            self.bi_list[-1].update_virtual_end(klc)
            return True

        # 尝试形成新的虚拟笔
        _tmp_klc = klc
        while _tmp_klc and _tmp_klc.idx > self[-1].end_klc.idx:
            assert _tmp_klc is not None
            if self.can_make_bi(_tmp_klc, self[-1].end_klc, for_virtual=True):
                self.add_new_bi(self.last_end, _tmp_klc, is_sure=False)
                return True
            elif self.update_peak(_tmp_klc, for_virtual=True):
                return True
            _tmp_klc = _tmp_klc.pre  # 向前查找
        return False

    def add_new_bi(self, pre_klc, cur_klc, is_sure=True):
        """
        创建新笔并加入列表

        参数:
            pre_klc: 笔的起始K线
            cur_klc: 笔的结束K线
            is_sure: 是否确认笔
        """
        self.bi_list.append(CBi(pre_klc, cur_klc, idx=len(self.bi_list), is_sure=is_sure))
        if len(self.bi_list) >= 2:
            self.bi_list[-2].next = self.bi_list[-1]
            self.bi_list[-1].pre = self.bi_list[-2]

    def satisfy_bi_span(self, klc: CKLine, last_end: CKLine):
        """
        检查两个分型之间是否满足笔的K线数量要求

        参数:
            klc: 候选结束K线
            last_end: 上一个结束K线

        返回:
            True 如果满足跨度要求

        缠论知识 - 笔的K线数量要求：
        - 严格模式（is_strict=True）：至少需要4根合并K线
        - 非严格模式：至少需要3根合并K线，且其中至少包含3根原始K线

        注意：非严格模式下，如果 klc 恰好是 last_end 的下一个K线，
        尾部没有足够K线判断，返回 False。
        """
        bi_span = self.get_klc_span(klc, last_end)
        if self.config.is_strict:
            return bi_span >= 4
        # 非严格模式：检查原始K线数量
        uint_kl_cnt = 0
        tmp_klc = last_end.next
        while tmp_klc:
            uint_kl_cnt += len(tmp_klc.lst)
            if not tmp_klc.next:  # 最后尾部虚笔时，可能 klc.idx == last_end.idx+1
                return False
            if tmp_klc.next.idx < klc.idx:
                tmp_klc = tmp_klc.next
            else:
                break
        return bi_span >= 3 and uint_kl_cnt >= 3

    def get_klc_span(self, klc: CKLine, last_end: CKLine) -> int:
        """
        计算两个分型K线之间的跨度（合并K线数量）

        参数:
            klc: 结束K线
            last_end: 起始K线

        返回:
            合并K线数量（如果有跳空且 gap_as_kl=True，每个跳空算1根K线）

        缠论知识 - 跳空算K线：
        如果 gap_as_kl=True，跳空缺口算作一根K线，这样笔更容易形成。
        这是为了处理跳空行情中笔形成困难的问题。
        """
        span = klc.idx - last_end.idx
        if not self.config.gap_as_kl:
            return span
        if span >= 4:  # 加速运算：已经满足严格模式要求，不需要精确计算跳空
            return span
        tmp_klc = last_end
        while tmp_klc and tmp_klc.idx < klc.idx:
            if tmp_klc.has_gap_with_next():
                span += 1  # 每个跳空额外算1根K线
            tmp_klc = tmp_klc.next
        return span

    def can_make_bi(self, klc: CKLine, last_end: CKLine, for_virtual: bool = False):
        """
        判断两个分型之间是否能形成一笔

        参数:
            klc: 候选结束K线
            last_end: 上一个结束K线
            for_virtual: 是否用于虚拟笔

        返回:
            True 如果满足笔的所有条件

        需要满足的条件：
        1. K线跨度满足要求（bi_algo='fx' 时跳过跨度检查）
        2. 分型验证通过（check_fx_valid）
        3. 端点满足极值条件（如果 bi_end_is_peak=True）
        """
        satisify_span = True if self.config.bi_algo == 'fx' else self.satisfy_bi_span(klc, last_end)
        if not satisify_span:
            return False
        if not last_end.check_fx_valid(klc, self.config.bi_fx_check, for_virtual):
            return False
        if self.config.bi_end_is_peak and not end_is_peak(last_end, klc):
            return False
        return True

    def try_update_end(self, klc: CKLine, for_virtual=False) -> bool:
        """
        尝试更新当前笔的结束点

        参数:
            klc: 新的候选结束K线
            for_virtual: 是否虚拟笔

        返回:
            True 如果成功更新

        条件：
        - 上升笔 + 顶分型 + 新高 > 当前结束值
        - 下降笔 + 底分型 + 新低 < 当前结束值

        Python 特性：嵌套函数（check_top/check_bottom）在函数内定义，只在函数内可见
        Java 对比：Java 不支持函数内定义函数，通常用 Lambda 或内部类
        """

        def check_top(klc: CKLine, for_virtual):
            """检查是否为顶分型（虚拟笔模式下检查方向）"""
            if for_virtual:
                return klc.dir == KLINE_DIR.UP
            else:
                return klc.fx == FX_TYPE.TOP

        def check_bottom(klc: CKLine, for_virtual):
            """检查是否为底分型（虚拟笔模式下检查方向）"""
            if for_virtual:
                return klc.dir == KLINE_DIR.DOWN
            else:
                return klc.fx == FX_TYPE.BOTTOM

        if len(self.bi_list) == 0:
            return False
        last_bi = self.bi_list[-1]
        if (last_bi.is_up() and check_top(klc, for_virtual) and klc.high >= last_bi.get_end_val()) or \
           (last_bi.is_down() and check_bottom(klc, for_virtual) and klc.low <= last_bi.get_end_val()):
            last_bi.update_virtual_end(klc) if for_virtual else last_bi.update_new_end(klc)
            self.last_end = klc
            return True
        else:
            return False

    def get_last_klu_of_last_bi(self) -> Optional[int]:
        """
        获取最后一笔的结束点所在原始K线索引
        返回: K线索引，如果没有笔则返回 None
        """
        return self.bi_list[-1].get_end_klu().idx if len(self) > 0 else None


def end_is_peak(last_end: CKLine, cur_end: CKLine) -> bool:
    """
    检查笔的端点是否满足极值条件

    参数:
        last_end: 笔的起始K线
        cur_end: 笔的结束K线

    返回:
        True 如果端点满足极值条件

    缠论知识 - 端点是极值：
    笔的端点必须是笔区间内的最高点或最低点：
    - 上升笔（底→顶）：from 底分型到顶分型之间，没有比顶分型更高的K线
    - 下降笔（顶→底）：from 顶分型到底分型之间，没有比底分型更低的K线

    如果中间有更高的K线，说明笔的端点选错了，需要调整。
    """
    if last_end.fx == FX_TYPE.BOTTOM:
        # 上升笔：检查从 last_end 到 cur_end 之间是否有比 cur_end 更高的K线
        cmp_thred = cur_end.high
        klc = last_end.get_next()
        while True:
            if klc.idx >= cur_end.idx:
                return True
            if klc.high > cmp_thred:
                return False  # 中间有更高的K线，端点不是极值
            klc = klc.get_next()
    elif last_end.fx == FX_TYPE.TOP:
        # 下降笔：检查从 last_end 到 cur_end 之间是否有比 cur_end 更低的K线
        cmp_thred = cur_end.low
        klc = last_end.get_next()
        while True:
            if klc.idx >= cur_end.idx:
                return True
            if klc.low < cmp_thred:
                return False  # 中间有更低的K线，端点不是极值
            klc = klc.get_next()
    return True