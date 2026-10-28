# -*- coding: utf-8 -*-
"""
笔模块 - 表示缠论中的"笔"，由顶底分型之间的K线构成

Java 开发者注意：
- @make_cache 是自定义缓存装饰器（见 Common/cache.py），类似于 Java 中的 @Cacheable 注解
- @property 把方法调用变成属性访问语法，类似于 Java 的 getter 但不需要 get 前缀
- Python 的 yield 是生成器关键字，类似于 Java 中实现 Iterator 接口
- Python 的 Optional[T] 类似于 Java 的 @Nullable T
"""

from typing import List, Optional

from Common.cache import make_cache
from Common.CEnum import BI_DIR, BI_TYPE, DATA_FIELD, FX_TYPE, MACD_ALGO
from Common.ChanException import CChanException, ErrCode
from KLine.KLine import CKLine
from KLine.KLine_Unit import CKLine_Unit


class CBi:
    """
    笔 - 缠论中连接相邻顶底分型的线段

    缠论知识 - 笔的定义：
    笔由相邻的顶分型和底分型连接而成，中间至少有一根独立的K线（不属于两个分型的K线）。
    - 上升笔：底分型→顶分型
    - 下降笔：顶分型→底分型

    笔的两种状态：
    - 确定笔（is_sure=True）：笔的结束点已经被后续走势确认
    - 虚拟笔（is_sure=False）：最后一笔尚未确认，可能在后续K线中被延伸或破坏

    属性说明：
    - begin_klc/end_klc: 起始/结束合并K线
    - dir: 方向（BI_DIR.UP 或 BI_DIR.DOWN）
    - idx: 笔的序号
    - type: 笔的类型（STRICT=严格笔）
    - is_sure: 是否是确认笔
    - seg_idx: 所属线段索引
    - parent_seg: 所属线段引用
    - bsp: 买卖点（如果笔的端点是买卖点）
    """

    def __init__(self, begin_klc: CKLine, end_klc: CKLine, idx: int, is_sure: bool):
        """
        初始化笔
        参数:
            begin_klc: 起始合并K线（分型所在K线）
            end_klc: 结束合并K线（分型所在K线）
            idx: 笔的序号
            is_sure: 是否已确认
        """
        self.__dir = None
        self.__idx = idx
        self.__type = BI_TYPE.STRICT

        self.set(begin_klc, end_klc)

        self.__is_sure = is_sure
        self.__used_to_be_sure = is_sure  # 记录曾经是否确认过（用于虚拟笔回退）
        self.__sure_end: List[CKLine] = []  # 历史确认结束点列表（用于虚拟笔恢复）

        self.__seg_idx: Optional[int] = None

        from Seg.Seg import CSeg
        self.parent_seg: Optional[CSeg[CBi]] = None  # 在哪个线段里面

        from BuySellPoint.BS_Point import CBS_Point
        self.bsp: Optional[CBS_Point] = None  # 尾部是不是买卖点

        self.next: Optional[CBi] = None
        self.pre: Optional[CBi] = None

    def clean_cache(self):
        """清空缓存字典，使 @make_cache 装饰的方法重新计算"""
        self._memoize_cache = {}

    # ===== 属性访问器 =====

    @property
    def begin_klc(self): return self.__begin_klc

    @property
    def end_klc(self): return self.__end_klc

    @property
    def dir(self): return self.__dir

    @property
    def idx(self): return self.__idx

    @property
    def type(self): return self.__type

    @property
    def is_sure(self): return self.__is_sure

    @property
    def used_to_be_sure(self): return self.__used_to_be_sure

    @property
    def is_used_to_be_sure(self): return self.is_sure or self.used_to_be_sure

    @property
    def sure_end(self): return self.__sure_end

    @property
    def klc_lst(self):
        """
        笔包含的合并K线的迭代器（从开始到结束）
        Python 语法：yield 是生成器，每次产出下一个元素
        Java 对比：需要实现 Iterator 接口，用 hasNext()/next() 方法
        """
        klc = self.begin_klc
        while True:
            yield klc
            klc = klc.next
            if not klc or klc.idx > self.end_klc.idx:
                break

    @property
    def klc_lst_re(self):
        """
        笔包含的合并K线的逆序迭代器（从结束到开始）
        用于反向遍历（如 MACD 半面积反向计算）
        """
        klc = self.end_klc
        while True:
            yield klc
            klc = klc.pre
            if not klc or klc.idx < self.begin_klc.idx:
                break

    @property
    def seg_idx(self): return self.__seg_idx

    def set_seg_idx(self, idx):
        """设置笔所属的线段索引"""
        self.__seg_idx = idx

    def __str__(self):
        """字符串表示，格式如 'UP|2024/01/01~2024/01/05 10.0->12.0 ~ 2024/01/06~2024/01/10 12.0->11.0'"""
        return f"{self.dir}|{self.begin_klc} ~ {self.end_klc}"

    def check(self):
        """
        校验笔的合法性
        检查项：
        - 下降笔：起始高点 > 结束低点
        - 上升笔：起始低点 < 结束高点
        Python 语法：raise ... from e 是异常链，类似于 Java 的 cause exception
        """
        try:
            if self.is_down():
                assert self.begin_klc.high > self.end_klc.low
            else:
                assert self.begin_klc.low < self.end_klc.high
        except Exception as e:
            raise CChanException(f"{self.idx}:{self.begin_klc[0].time}~{self.end_klc[-1].time}笔的方向和收尾位置不一致!", ErrCode.BI_ERR) from e

    def set(self, begin_klc: CKLine, end_klc: CKLine):
        """
        设置笔的起始和结束K线，自动推断方向

        方向推断规则：
        - 起始K线是底分型 → 上升笔（UP）
        - 起始K线是顶分型 → 下降笔（DOWN）
        """
        self.__begin_klc: CKLine = begin_klc
        self.__end_klc: CKLine = end_klc
        if begin_klc.fx == FX_TYPE.BOTTOM:
            self.__dir = BI_DIR.UP
        elif begin_klc.fx == FX_TYPE.TOP:
            self.__dir = BI_DIR.DOWN
        else:
            raise CChanException("ERROR DIRECTION when creating bi", ErrCode.BI_ERR)
        self.check()
        self.clean_cache()

    @make_cache
    def get_begin_val(self):
        """
        获取笔的起始值
        - 上升笔：起始低点
        - 下降笔：起始高点
        """
        return self.begin_klc.low if self.is_up() else self.begin_klc.high

    @make_cache
    def get_end_val(self):
        """
        获取笔的结束值
        - 上升笔：结束高点
        - 下降笔：结束低点
        """
        return self.end_klc.high if self.is_up() else self.end_klc.low

    @make_cache
    def get_begin_klu(self) -> CKLine_Unit:
        """
        获取笔起始点所在的原始K线单元
        缠论知识：笔的起始点必须是分型中的极值点
        上升笔：起始为底分型，取最低点所在的K线
        下降笔：起始为顶分型，取最高点所在的K线
        """
        if self.is_up():
            return self.begin_klc.get_peak_klu(is_high=False)
        else:
            return self.begin_klc.get_peak_klu(is_high=True)

    @make_cache
    def get_end_klu(self) -> CKLine_Unit:
        """
        获取笔结束点所在的原始K线单元
        上升笔：结束为顶分型，取最高点所在的K线
        下降笔：结束为底分型，取最低点所在的K线
        """
        if self.is_up():
            return self.end_klc.get_peak_klu(is_high=True)
        else:
            return self.end_klc.get_peak_klu(is_high=False)

    @make_cache
    def amp(self):
        """
        笔的振幅（绝对值）
        返回: |结束值 - 起始值|
        缠论知识：笔的振幅用于判断笔的力度和背驰
        """
        return abs(self.get_end_val() - self.get_begin_val())

    @make_cache
    def get_klu_cnt(self):
        """笔包含的原始K线数量"""
        return self.get_end_klu().idx - self.get_begin_klu().idx + 1

    @make_cache
    def get_klc_cnt(self):
        """笔包含的合并K线数量"""
        assert self.end_klc.idx == self.get_end_klu().klc.idx
        assert self.begin_klc.idx == self.get_begin_klu().klc.idx
        return self.end_klc.idx - self.begin_klc.idx + 1

    @make_cache
    def _high(self):
        """
        笔的最高点
        - 上升笔：结束点（顶分型）的高点
        - 下降笔：起始点（顶分型）的高点
        """
        return self.end_klc.high if self.is_up() else self.begin_klc.high

    @make_cache
    def _low(self):
        """
        笔的最低点
        - 上升笔：起始点（底分型）的低点
        - 下降笔：结束点（底分型）的低点
        """
        return self.begin_klc.low if self.is_up() else self.end_klc.low

    @make_cache
    def _mid(self):
        """笔的中位价 = (最高点 + 最低点) / 2"""
        return (self._high() + self._low()) / 2

    @make_cache
    def is_down(self):
        """是否为下降笔"""
        return self.dir == BI_DIR.DOWN

    @make_cache
    def is_up(self):
        """是否为上升笔"""
        return self.dir == BI_DIR.UP

    def update_virtual_end(self, new_klc: CKLine):
        """
        更新虚拟笔的结束点

        缠论知识 - 虚拟笔：
        当最后一笔尚未确认时，如果行情继续朝同一方向延伸，
        笔的结束点需要更新为新的K线。

        行为：
        1. 将当前结束点加入确认结束历史列表
        2. 更新结束点为 new_klc
        3. 标记为未确认状态
        """
        self.append_sure_end(self.end_klc)
        self.update_new_end(new_klc)
        self.__used_to_be_sure = self.__is_sure
        self.__is_sure = False

    def restore_from_virtual_end(self, sure_end: CKLine):
        """
        从虚拟笔恢复到确认状态

        当后面的K线形成反向分型，确认了前面的笔结束时调用。
        恢复为确认状态，并将结束点设为确认的结束点。
        """
        self.__is_sure = True
        self.__used_to_be_sure = True
        self.update_new_end(new_klc=sure_end)
        self.__sure_end = []

    def append_sure_end(self, klc: CKLine):
        """记录一个确认过的结束点"""
        self.__sure_end.append(klc)

    def update_new_end(self, new_klc: CKLine):
        """
        更新结束点并重新校验
        """
        self.__end_klc = new_klc
        self.check()
        self.clean_cache()

    def cal_macd_metric(self, macd_algo, is_reverse):
        """
        根据算法类型计算 MACD 背驰指标

        参数:
            macd_algo: MACD 算法类型（MACD_ALGO 枚举）
            is_reverse: 是否反向计算（用于 AREA 算法）

        返回:
            对应算法计算的指标值

        缠论知识 - 背驰判断：
        背驰通过比较相邻同向笔的 MACD 指标来判断：
        - 面积法（AREA/FULL_AREA）：比较 MACD 柱的面积
        - 峰值法（PEAK）：比较 MACD 柱的峰值
        - 差值法（DIFF）：比较 MACD 柱的最大差值
        - 斜率法（SLOPE）：比较价格变化率
        - 振幅法（AMP）：比较价格振幅
        - 成交量法（VOLUMN/AMOUNT）：比较成交量/成交额
        """
        if macd_algo == MACD_ALGO.AREA:
            return self.Cal_MACD_half(is_reverse)
        elif macd_algo == MACD_ALGO.PEAK:
            return self.Cal_MACD_peak()
        elif macd_algo == MACD_ALGO.FULL_AREA:
            return self.Cal_MACD_area()
        elif macd_algo == MACD_ALGO.DIFF:
            return self.Cal_MACD_diff()
        elif macd_algo == MACD_ALGO.SLOPE:
            return self.Cal_MACD_slope()
        elif macd_algo == MACD_ALGO.AMP:
            return self.Cal_MACD_amp()
        elif macd_algo == MACD_ALGO.AMOUNT:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNOVER, cal_avg=False)
        elif macd_algo == MACD_ALGO.VOLUMN:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_VOLUME, cal_avg=False)
        elif macd_algo == MACD_ALGO.VOLUMN_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_VOLUME, cal_avg=True)
        elif macd_algo == MACD_ALGO.AMOUNT_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNOVER, cal_avg=True)
        elif macd_algo == MACD_ALGO.TURNRATE_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNRATE, cal_avg=True)
        elif macd_algo == MACD_ALGO.RSI:
            return self.Cal_Rsi()
        else:
            raise CChanException(f"unsupport macd_algo={macd_algo}, should be one of area/full_area/peak/diff/slope/amp", ErrCode.PARA_ERROR)

    @make_cache
    def Cal_Rsi(self):
        """
        计算笔的 RSI 指标
        - 下降笔：返回 10000 / min(rsi)，RSI 越低越超卖
        - 上升笔：返回 max(rsi)，RSI 越高越超买

        缠论知识：RSI 背驰 — 价格创新高/低但 RSI 没有同步创新高/低
        """
        rsi_lst: List[float] = []
        for klc in self.klc_lst:
            rsi_lst.extend(klu.rsi for klu in klc.lst)
        return 10000.0/(min(rsi_lst)+1e-7) if self.is_down() else max(rsi_lst)

    @make_cache
    def Cal_MACD_area(self):
        """
        计算笔的 MACD 全面积

        全面积 = 笔区间内所有同向 MACD 柱的绝对值之和
        - 上升笔：累加所有 MACD > 0 的柱面积
        - 下降笔：累加所有 MACD < 0 的柱面积

        缠论知识：MACD 面积背驰 — 价格创新高但 MACD 红柱面积减小
        """
        _s = 1e-7
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        for klc in self.klc_lst:
            for klu in klc.lst:
                if klu.idx < begin_klu.idx or klu.idx > end_klu.idx:
                    continue
                if (self.is_down() and klu.macd.macd < 0) or (self.is_up() and klu.macd.macd > 0):
                    _s += abs(klu.macd.macd)
        return _s

    @make_cache
    def Cal_MACD_peak(self):
        """
        计算笔的 MACD 峰值

        峰值 = 笔区间内同向 MACD 柱的最大绝对值
        - 上升笔：MACD > 0 的最大柱
        - 下降笔：MACD < 0 的最大柱（绝对值）

        缠论知识：MACD 峰值背驰 — 价格创新高但 MACD 红柱峰值降低
        """
        peak = 1e-7
        for klc in self.klc_lst:
            for klu in klc.lst:
                if abs(klu.macd.macd) > peak:
                    if self.is_down() and klu.macd.macd < 0:
                        peak = abs(klu.macd.macd)
                    elif self.is_up() and klu.macd.macd > 0:
                        peak = abs(klu.macd.macd)
        return peak

    def Cal_MACD_half(self, is_reverse):
        """
        计算笔的 MACD 半面积

        半面积 = 从笔的起始端开始，累加同向 MACD 柱，直到柱子方向改变就停止

        参数:
            is_reverse: True=从结束端反向计算，False=从起始端正向计算

        缠论知识：MACD 半面积法 — 只计算 MACD 柱方向一致的部分面积，
        当 MACD 柱方向改变时停止累加，避免包含反向MACD柱
        """
        if is_reverse:
            return self.Cal_MACD_half_reverse()
        else:
            return self.Cal_MACD_half_obverse()

    @make_cache
    def Cal_MACD_half_obverse(self):
        """
        正向半面积计算：从笔的起始端向结束端累加

        从起始K线开始，累加同向MACD柱的绝对值，
        当遇到反向MACD柱时停止累加。

        Python 语法：for...else 是 Python 特有语法
        else 块在 for 循环正常结束（没有被 break）时执行
        Java 对比：需要用一个 boolean 标志变量来模拟
        """
        _s = 1e-7
        begin_klu = self.get_begin_klu()
        peak_macd = begin_klu.macd.macd  # 参考方向：起始K线的MACD值
        for klc in self.klc_lst:
            for klu in klc.lst:
                if klu.idx < begin_klu.idx:
                    continue
                if klu.macd.macd*peak_macd > 0:  # 同向（乘积>0表示同号）
                    _s += abs(klu.macd.macd)
                else:
                    break  # MACD方向改变，停止累加
            else:  # for...else：内层循环正常结束（没有被break），继续外层循环
                continue
            break  # 内层循环被break了，外层也停止
        return _s

    @make_cache
    def Cal_MACD_half_reverse(self):
        """
        反向半面积计算：从笔的结束端向起始端累加

        从结束K线开始，向起始方向累加同向MACD柱的绝对值，
        当遇到反向MACD柱时停止累加。
        """
        _s = 1e-7
        begin_klu = self.get_end_klu()
        peak_macd = begin_klu.macd.macd
        for klc in self.klc_lst_re:
            for klu in klc[::-1]:  # Python 语法：[::-1] 是列表反转切片
                if klu.idx > begin_klu.idx:
                    continue
                if klu.macd.macd*peak_macd > 0:
                    _s += abs(klu.macd.macd)
                else:
                    break
            else:
                continue
            break
        return _s

    @make_cache
    def Cal_MACD_diff(self):
        """
        MACD 红绿柱最大值与最小值之差

        缠论知识：MACD 差值法 — 比较笔区间内 MACD 柱的波动幅度
        差值越大说明 MACD 指标波动越剧烈
        """
        _max, _min = float("-inf"), float("inf")
        for klc in self.klc_lst:
            for klu in klc.lst:
                macd = klu.macd.macd
                if macd > _max:
                    _max = macd
                if macd < _min:
                    _min = macd
        return _max-_min

    @make_cache
    def Cal_MACD_slope(self):
        """
        计算笔的斜率指标

        上升笔：(结束高点 - 起始低点) / 结束高点 / (K线数量)
        下降笔：(起始高点 - 结束低点) / 起始高点 / (K线数量)

        缠论知识：斜率法 — 价格变化率，斜率越大笔的力度越强
        """
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_up():
            return (end_klu.high - begin_klu.low)/end_klu.high/(end_klu.idx - begin_klu.idx + 1)
        else:
            return (begin_klu.high - end_klu.low)/begin_klu.high/(end_klu.idx - begin_klu.idx + 1)

    @make_cache
    def Cal_MACD_amp(self):
        """
        计算笔的振幅指标

        下降笔：(起始高点 - 结束低点) / 起始高点
        上升笔：(结束高点 - 起始低点) / 起始低点

        缠论知识：振幅法 — 笔的价格变化幅度，振幅越大笔的力度越强
        """
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_down():
            return (begin_klu.high-end_klu.low)/begin_klu.high
        else:
            return (end_klu.high-begin_klu.low)/begin_klu.low

    def Cal_MACD_trade_metric(self, metric: str, cal_avg=False) -> float:
        """
        计算交易量指标（成交量/成交额/换手率）

        参数:
            metric: 指标字段名
            cal_avg: True=按K线数取平均，False=求和

        缠论知识：成交量背驰 — 价格创新高但成交量萎缩，说明上涨动力不足
        """
        _s = 0
        for klc in self.klc_lst:
            for klu in klc.lst:
                metric_res = klu.trade_info.metric[metric]
                if metric_res is None:
                    return 0.0
                _s += metric_res
        return _s / self.get_klu_cnt() if cal_avg else _s