# -*- coding: utf-8 -*-
"""
线段配置模块 - 线段计算的各项参数配置

Java 开发者注意：
- Python 类没有构造函数重载，通过默认参数实现可选参数
- 枚举值转换在 __init__ 中进行（字符串 → 枚举），类似于 Java 的工厂方法模式
"""

from Common.CEnum import LEFT_SEG_METHOD
from Common.ChanException import CChanException, ErrCode


class CSegConfig:
    """
    线段的配置参数

    属性说明：
    - seg_algo: 线段算法（"chan"=特征序列法，默认推荐）
    - left_method: 尾部未确认部分的处理方式
      - "peak": 找极值点作为虚段（默认）
      - "all": 全部收集为一个虚段

    缠论知识 - 线段尾部处理：
    由于线段需要被后续线段破坏后才能确认，最后一段往往未确认。
    left_method 决定了如何处理末尾未确认的笔：
    - PEAK: 找极值笔作为虚拟线段
    - ALL: 把所有剩余笔合并为一个虚拟线段
    """

    def __init__(self, seg_algo="chan", left_method="peak"):
        """初始化线段配置"""
        self.seg_algo = seg_algo
        if left_method == "all":
            self.left_method = LEFT_SEG_METHOD.ALL
        elif left_method == "peak":
            self.left_method = LEFT_SEG_METHOD.PEAK
        else:
            raise CChanException(f"unknown left_seg_method={left_method}", ErrCode.PARA_ERROR)