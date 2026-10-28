# -*- coding: utf-8 -*-
"""
中枢配置模块 - 中枢计算的各项参数配置

Java 开发者注意：
- Python 类属性在 __init__ 中动态定义，不需要像 Java 那样先声明
- 默认参数值在函数定义时计算，类似于 Java 的方法重载默认值
"""


class CZSConfig:
    """
    中枢的配置参数

    属性说明：
    - need_combine: 是否需要合并相邻的中枢
    - zs_combine_mode: 中枢合并模式
      - "zs": 中枢区间有重叠才合并
      - "peak": 中枢极值区间有重叠就合并（更宽松）
    - one_bi_zs: 是否允许一笔中枢（默认 False）
    - zs_algo: 中枢算法
      - "normal": 标准算法（按线段计算）
      - "over_seg": 跨线段算法
      - "auto": 自动选择

    缠论知识 - 中枢合并：
    当相邻两个中枢的区间有重叠时，需要合并为一个更大的中枢。
    合并后的中枢区间取两个中枢的并集。
    """

    def __init__(self, need_combine=True, zs_combine_mode="zs", one_bi_zs=False, zs_algo="normal"):
        self.need_combine = need_combine
        self.zs_combine_mode = zs_combine_mode
        self.one_bi_zs = one_bi_zs
        self.zs_algo = zs_algo