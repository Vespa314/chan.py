# -*- coding: utf-8 -*-
"""
异常类定义模块

Java 开发者注意：
- Python 的异常继承自 Exception，类似于 Java 的 Exception
- Python 没有 checked exception，所有异常都是 unchecked
- IntEnum 是 Python 特有的，既有 int 的特性又有 Enum 的特性
- __init__ 中调用父类构造函数用 Exception.__init__(self, message)，而不是 super().__init__(message)
"""

from enum import IntEnum


class ErrCode(IntEnum):
    """
    错误码枚举，继承自 IntEnum（Python 特有的 int+Enum 混合类型）
    错误码分为三段：
    - 0~99: 缠论计算错误
    - 100~199: 交易错误
    - 200~299: K线数据错误
    Java 对比：类似于定义一个包含 int code 和 String message 的 Enum
    """

    # ===== 缠论相关错误 (0~99) =====
    _CHAN_ERR_BEGIN = 0
    COMMON_ERROR = 1          # 通用错误
    SRC_DATA_NOT_FOUND = 3    # 数据源未找到数据
    SRC_DATA_TYPE_ERR = 4     # 数据源类型错误
    PARA_ERROR = 5            # 参数错误
    EXTRA_KLU_ERR = 6         # 额外K线数据错误
    SEG_END_VALUE_ERR = 7     # 线段起点终点值不匹配
    SEG_EIGEN_ERR = 8         # 特征序列错误
    BI_ERR = 9                # 笔错误
    COMBINER_ERR = 10         # 合并器错误
    PLOT_ERR = 11             # 绘图错误
    MODEL_ERROR = 12          # 模型错误
    SEG_LEN_ERR = 13          # 线段长度错误
    ENV_CONF_ERR = 14         # 环境配置错误
    UNKNOWN_DB_TYPE = 15      # 未知数据库类型
    FEATURE_ERROR = 16        # 特征错误
    CONFIG_ERROR = 17         # 配置错误
    SRC_DATA_FORMAT_ERROR = 18  # 数据源格式错误
    _CHAN_ERR_END = 99

    # ===== 交易相关错误 (100~199) =====
    _TRADE_ERR_BEGIN = 100
    SIGNAL_EXISTED = 101           # 信号已存在
    RECORD_NOT_EXIST = 102         # 记录不存在
    RECORD_ALREADY_OPENED = 103    # 记录已开仓
    QUOTA_NOT_ENOUGH = 104         # 配额不足
    RECORD_NOT_OPENED = 105        # 记录未开仓
    TRADE_UNLOCK_FAIL = 106        # 交易解锁失败
    PLACE_ORDER_FAIL = 107         # 下单失败
    LIST_ORDER_FAIL = 108          # 查询订单失败
    CANDEL_ORDER_FAIL = 109        # 撤单失败
    GET_FUTU_PRICE_FAIL = 110      # 获取富途报价失败
    GET_FUTU_LOT_SIZE_FAIL = 111   # 获取富途每手股数失败
    OPEN_RECORD_NOT_WATCHING = 112  # 开仓记录不在监控中
    GET_HOLDING_QTY_FAIL = 113     # 获取持仓数量失败
    RECORD_CLOSED = 114            # 记录已关闭
    REQUEST_TRADING_DAYS_FAIL = 115  # 获取交易日失败
    COVER_ORDER_ID_NOT_UNIQUE = 116  # 平仓订单ID不唯一
    SIGNAL_TRADED = 117            # 信号已交易
    _TRADE_ERR_END = 199

    # ===== K线数据错误 (200~299) =====
    _KL_ERR_BEGIN = 200
    PRICE_BELOW_ZERO = 201         # 价格低于零
    KL_DATA_NOT_ALIGN = 202        # K线数据不对齐
    KL_DATA_INVALID = 203          # K线数据无效
    KL_TIME_INCONSISTENT = 204     # K线时间不一致
    TRADEINFO_TOO_MUCH_ZERO = 205  # 交易指标太多零值
    KL_NOT_MONOTONOUS = 206        # K线时间非单调递增
    SNAPSHOT_ERR = 207             # 快照错误
    SUSPENSION = 208               # 疑似停牌
    STOCK_IPO_TOO_LATE = 209       # 股票上市太晚
    NO_DATA = 210                  # 没有数据
    STOCK_NOT_ACTIVE = 211         # 股票不活跃
    STOCK_PRICE_NOT_ACTIVE = 212   # 股价不活跃
    _KL_ERR_END = 299


class CChanException(Exception):
    """
    缠论异常类
    包含错误码(errcode)和错误消息(msg)
    Java 对比：类似于自定义 Exception 子类，包含额外的 int code 字段
    """

    def __init__(self, message, code=ErrCode.COMMON_ERROR):
        """
        创建缠论异常
        参数:
            message: 错误消息
            code: 错误码，默认为 COMMON_ERROR
        """
        self.errcode = code
        self.msg = message
        Exception.__init__(self, message)
        # Python 特性：调用父类构造函数用 Exception.__init__(self, message)
        # Java 对比：Java 用 super(message)

    def is_kldata_err(self):
        """
        判断是否是 K 线数据相关的错误
        Python 特性：IntEnum 可以直接比较大小，这是 Java Enum 做不到的
        """
        return ErrCode._KL_ERR_BEGIN < self.errcode < ErrCode._KL_ERR_END

    def is_chan_err(self):
        """判断是否是缠论计算相关的错误"""
        return ErrCode._CHAN_ERR_BEGIN < self.errcode < ErrCode._CHAN_ERR_END


if __name__ == "__main__":
    """
    Python 特有的模块入口：if __name__ == "__main__" 相当于 Java 的 public static void main(String[] args)
    此处演示了 Python 3.11 和 Python 3.8 中 IntEnum 的 __str__ 行为差异
    - Python 3.8: 打印 ErrCode.CONFIG_ERROR 显示 "ErrCode.CONFIG_ERROR"
    - Python 3.11: 打印 ErrCode.CONFIG_ERROR 显示 "17"（int 值）
    """
    def foo():
        raise CChanException("XXX", ErrCode.CONFIG_ERROR)

    try:
        foo()
    except CChanException as e:
        # Python 的 except 类似于 Java 的 catch
        # as e 类似于 Java 的 catch (CChanException e)
        print(str(e.errcode))
        # python3.8 结果为：ErrCode.CONFIG_ERROR
        # python3.11 结果为：17

        print(e.errcode.name, type(e.errcode.name))
        # Python 特性：.name 获取枚举名称，类似于 Java 的 .name()