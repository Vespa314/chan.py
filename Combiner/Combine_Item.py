# -*- coding: utf-8 -*-
"""
合并元素包装类 - 统一 CKLine_Unit、CBi、CSeg 的接口，使它们可以共用 CKLine_Combiner

Java 开发者注意：
- isinstance(item, CBi) 类似于 Java 的 instanceof 运算符
- 这是 Python 的"鸭子类型"思想的一种变体：不依赖继承，而是通过包装器统一接口
- 延迟导入（函数内 import）是为了避免循环引用，Python 中很常见
"""

from Common.ChanException import CChanException, ErrCode


class CCombine_Item:
    """
    合并元素包装器
    将 CBi（笔）、CKLine_Unit（单根K线）、CSeg（线段）三种类型统一包装
    提供 time_begin, time_end, high, low 四个统一属性

    设计模式：适配器模式（Adapter Pattern）
    这使得 CKLine_Combiner 可以同时用于：
    - K 线合并（包装 CKLine_Unit）
    - 特征序列合并（包装 CBi）
    - 线段的线段合并（包装 CSeg）
    """

    def __init__(self, item):
        """
        初始化包装器，根据 item 类型提取统一属性
        参数:
            item: CBi 或 CKLine_Unit 或 CSeg 类型
        Python 特性：延迟导入（函数内 import）避免循环引用
        循环引用背景：CBi 引用 CKLine_Unit，CKLine_Combiner 引用 CCombine_Item，
                      CCombine_Item 又需要引用 CBi 和 CKLine_Unit
        Java 对比：Java 中 import 是包级别的，不会出现循环引用问题
        """
        from Bi.Bi import CBi
        from KLine.KLine_Unit import CKLine_Unit
        from Seg.Seg import CSeg

        if isinstance(item, CBi):
            # 笔：时间范围用 begin_klc.idx 和 end_klc.idx，高低点用笔的 _high()/_low()
            self.time_begin = item.begin_klc.idx
            self.time_end = item.end_klc.idx
            self.high = item._high()
            self.low = item._low()
        elif isinstance(item, CKLine_Unit):
            # 单根K线：时间范围就是自身时间，高低点直接取
            self.time_begin = item.time
            self.time_end = item.time
            self.high = item.high
            self.low = item.low
        elif isinstance(item, CSeg):
            # 线段：时间范围用 start_bi.begin_klc.idx 和 end_bi.end_klc.idx
            self.time_begin = item.start_bi.begin_klc.idx
            self.time_end = item.end_bi.end_klc.idx
            self.high = item._high()
            self.low = item._low()
        else:
            raise CChanException(f"{type(item)} is unsupport sub class of CCombine_Item", ErrCode.COMMON_ERROR)