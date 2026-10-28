# -*- coding: utf-8 -*-
"""
笔配置模块 - 笔计算的各项参数配置

Java 开发者注意：
- Python 类没有构造函数重载，通过默认参数实现可选参数
  Java 对比：Java 可以写多个构造函数（重载），Python 用默认参数值
- Python 的 __init__ 是构造函数，类似于 Java 的构造函数
- 类属性在 __init__ 中动态定义，不需要像 Java 那样先声明
"""

from Common.CEnum import FX_CHECK_METHOD
from Common.ChanException import CChanException, ErrCode


class CBiConfig:
    """
    笔的配置参数

    属性说明：
    - bi_algo: 笔的算法（"normal"=标准笔，"fx"=仅分型判断）
    - is_strict: 是否严格模式（K线数量要求更严格）
    - bi_fx_check: 分型验证方法（STRICT/LOSS/HALF/TOTALLY）
    - gap_as_kl: 跳空是否算作一根K线
    - bi_end_is_peak: 笔的端点是否必须是极值点
    - bi_allow_sub_peak: 是否允许次高点/次低点作为笔的端点
    """

    def __init__(
        self,
        bi_algo="normal",
        is_strict=True,
        bi_fx_check="half",
        gap_as_kl=True,
        bi_end_is_peak=True,
        bi_allow_sub_peak=True,
    ):
        """
        初始化笔配置

        参数:
            bi_algo: 笔算法。normal=标准笔（需要K线数量满足条件），fx=仅分型判断
            is_strict: 严格模式。True=至少4根合并K线，False=至少3根（含3根原始K线）
            bi_fx_check: 分型验证方法字符串。strict=严格，loss=宽松，half=半严格，totally=完全严格
            gap_as_kl: 跳空处理。True=将跳空缺口算作一根K线，让笔更容易形成
            bi_end_is_peak: 是否要求笔的端点必须是极值点。True=中间K线不能超过端点
            bi_allow_sub_peak: 是否允许次高点/次低点作为笔的端点
        """
        self.bi_algo = bi_algo
        self.is_strict = is_strict

        # 将字符串配置转换为枚举值
        if bi_fx_check == "strict":
            self.bi_fx_check = FX_CHECK_METHOD.STRICT
        elif bi_fx_check == "loss":
            self.bi_fx_check = FX_CHECK_METHOD.LOSS
        elif bi_fx_check == "half":
            self.bi_fx_check = FX_CHECK_METHOD.HALF
        elif bi_fx_check == 'totally':
            self.bi_fx_check = FX_CHECK_METHOD.TOTALLY
        else:
            raise CChanException(f"unknown bi_fx_check={bi_fx_check}", ErrCode.PARA_ERROR)

        self.gap_as_kl = gap_as_kl
        self.bi_end_is_peak = bi_end_is_peak
        self.bi_allow_sub_peak = bi_allow_sub_peak