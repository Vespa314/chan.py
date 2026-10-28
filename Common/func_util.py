# -*- coding: utf-8 -*-
"""
通用工具函数模块

Java 开发者注意：
- Python 函数不需要声明返回类型，类型注解是可选的（这里的 .前导 . 表示相对导入）
- 模块级函数类似于 Java 的 static 方法
- from .CEnum import ... 中的 . 表示当前包（相对导入），类似于 Java 的同包导入
"""

from .CEnum import BI_DIR, KL_TYPE


def kltype_lt_day(_type: KL_TYPE):
    """
    判断 K 线级别是否小于日线（即是否是分钟线/秒线等日内级别）
    参数:
        _type: K线级别
    返回:
        True 如果级别值 < K_DAY.value (15)
    使用场景：日内级别需要特殊的 K 线时间对齐处理
    """
    return _type.value < KL_TYPE.K_DAY.value


def kltype_lte_day(_type: KL_TYPE):
    """
    判断 K 线级别是否小于等于日线
    参数:
        _type: K线级别
    返回:
        True 如果级别值 <= K_DAY.value (15)
    使用场景：日线及以下级别需要进行父子 K 线时间一致性检查
    """
    return _type.value <= KL_TYPE.K_DAY.value


def check_kltype_order(type_list):
    """
    检查级别列表是否从大到小排列
    参数:
        type_list: K线级别列表
    抛出:
        AssertionError 如果顺序不是从大到小
    使用场景：CChan 初始化时要求 lv_list 必须从大级别到小级别
    Python 特性：assert 语句在 Python 中默认启用，Java 中需要 -ea 参数
    """
    last_lv = type_list[0].value
    for kl_type in type_list[1:]:
        assert kl_type.value < last_lv, "lv_list的顺序必须从大级别到小级别"
        last_lv = kl_type.value


def revert_bi_dir(dir):
    """
    反转笔方向
    参数:
        dir: BI_DIR.UP 或 BI_DIR.DOWN
    返回:
        BI_DIR.DOWN 或 BI_DIR.UP
    使用场景：特征序列中，上升线段要找下降笔的底分型，需要反转方向
    Python 特性：三元表达式 x if cond else y，类似于 Java 的 cond ? x : y
    """
    return BI_DIR.DOWN if dir == BI_DIR.UP else BI_DIR.UP


def has_overlap(l1, h1, l2, h2, equal=False):
    """
    判断两个区间 [l1, h1] 和 [l2, h2] 是否有重叠
    参数:
        l1/h1: 区间1的低点/高点
        l2/h2: 区间2的低点/高点
        equal: 是否允许边界相等算重叠（默认 False）
    返回:
        True 如果两个区间有重叠
    使用场景：
        - 中枢形成判断：三笔必须有重叠区间
        - 中枢合并判断：两个中枢区间是否有重叠
        - K线跳空判断：两K线价格区间是否有重叠
    缠论知识：中枢 = 至少三笔重叠的区间，重叠判断是中枢计算的基础
    """
    return h2 >= l1 and h1 >= l2 if equal else h2 > l1 and h1 > l2


def str2float(s):
    """
    字符串转浮点数，转换失败返回 0.0
    参数:
        s: 字符串
    返回:
        浮点数，转换失败返回 0.0
    使用场景：解析数据源返回的字符串数据（如 BaoStock 返回的 K 线数据）
    Python 特性：try/except ValueError 是 Python 的异常处理方式，Java 用 try/catch NumberFormatException
    """
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_inf(v):
    """
    解析无穷大值，将 float('inf') 转换为字符串表达式 'float("inf")'
    参数:
        v: 输入值
    返回:
        如果 v 是 float('inf') 或 float('-inf')，返回字符串表达式；否则返回原值
    使用场景：配置参数中使用无穷大作为"保送"（无条件通过）标记
    为什么需要：Python 的 eval/exec 不能直接处理 float('inf') 对象，需要转成字符串
    """
    if isinstance(v, float):
        if v == float("inf"):
            v = 'float("inf")'
        if v == float("-inf"):
            v = 'float("-inf")'
    return v