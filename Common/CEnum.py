# -*- coding: utf-8 -*-
"""
枚举类定义模块 - 定义项目中所有枚举类型

Java 开发者注意：
- Python 的 Enum 类似于 Java 的 Enum
- auto() 自动分配值，类似于 Java 的 ordinal()
- 和 Java 不同，Python 枚举值可以是任意类型（这里混用了 int 和 str）
- 访问方式：KL_TYPE.K_DAY（和 Java 一样）
"""

from enum import Enum, auto
from typing import Literal


class DATA_SRC(Enum):
    """
    数据源类型枚举
    注意：和 Java 不同，Python 不需要在 Enum 中声明构造函数和字段
    """
    BAO_STOCK = auto()  # BaoStock 数据源（默认 A 股数据源）
    CCXT = auto()       # CCXT 加密货币数据源
    CSV = auto()        # 本地 CSV 文件数据源
    AKSHARE = auto()    # Akshare 数据源（支持 A 股/港股/美股）


class KL_TYPE(Enum):
    """
    K 线级别枚举
    值越大级别越高，KL_TYPE.K_DAY.value = 15
    级别从低到高：1秒 → 3秒 → ... → 1分钟 → ... → 日线 → 周线 → 月线 → 季线 → 年线
    """
    K_1S = 1       # 1秒线
    K_3S = 2       # 3秒线
    K_5S = 3       # 5秒线
    K_10S = 4      # 10秒线
    K_15S = 5      # 15秒线
    K_20S = 6      # 20秒线
    K_30S = 7      # 30秒线
    K_1M = 8       # 1分钟线
    K_3M = 9       # 3分钟线
    K_5M = 10      # 5分钟线
    K_10M = 11     # 10分钟线
    K_15M = 12     # 15分钟线
    K_30M = 13     # 30分钟线
    K_60M = 14     # 60分钟线（小时线）
    K_DAY = 15     # 日线
    K_WEEK = 16    # 周线
    K_MON = 17     # 月线
    K_QUARTER = 18  # 季线
    K_YEAR = 19    # 年线


class KLINE_DIR(Enum):
    """K线方向枚举 - 用于描述单根K线或合并K线的方向"""
    UP = auto()       # 向上
    DOWN = auto()     # 向下
    COMBINE = auto()  # 合并中（包含处理时，两根K线需要合并）
    INCLUDED = auto()  # 被包含（被前一根K线完全包含，不参与合并）


class FX_TYPE(Enum):
    """分型类型枚举 - 缠论中的顶分型和底分型"""
    BOTTOM = auto()  # 底分型：中间K线最低点最低，且中间K线最高点最低
    TOP = auto()     # 顶分型：中间K线最高点最高，且中间K线最低点最高
    UNKNOWN = auto()  # 未知（尚未形成分型）


class BI_DIR(Enum):
    """笔的方向枚举"""
    UP = auto()    # 上升笔（从底分型到顶分型）
    DOWN = auto()  # 下降笔（从顶分型到底分型）


class BI_TYPE(Enum):
    """笔的类型枚举 - 描述笔是如何形成的"""
    UNKNOWN = auto()        # 未知类型
    STRICT = auto()         # 严格笔：顶底分型之间至少间隔4根合并K线
    SUB_VALUE = auto()      # 次高低点成笔：允许次高点/次低点作为笔的端点
    TIAOKONG_THRED = auto()  # 跳空阈值笔
    DAHENG = auto()         # 打横笔（横向整理）
    TUIBI = auto()          # 推笔
    UNSTRICT = auto()       # 非严格笔（宽松条件）
    TIAOKONG_VALUE = auto()  # 跳空值笔


# Python 特有的 Literal 类型注解：限制变量只能是 '1', '2', '3' 三个值之一
# Java 对比：Java 没有直接的 literal type，通常用 Enum 或 String 常量代替
BSP_MAIN_TYPE = Literal['1', '2', '3']


class BSP_TYPE(Enum):
    """
    买卖点类型枚举
    注意：和 Java 不同，Python 枚举的 value 可以是字符串
    main_type() 方法返回买卖点的主类型（1/2/3）
    """
    T1 = '1'     # 一类买卖点：趋势背驰产生，是最重要的买卖点
    T1P = '1p'   # 盘整背驰一类买卖点：没有完整中枢的背驰
    T2 = '2'     # 二类买卖点：一类买卖点之后的第一笔回撤
    T2S = '2s'   # 类二类买卖点：中枢内与二类同侧的其他买卖点
    T3A = '3a'   # 三类买卖点-after：中枢在一类之后，离开中枢后回抽不进入
    T3B = '3b'   # 三类买卖点-before：中枢在一类之前，离开中枢后回抽不进入

    def main_type(self) -> BSP_MAIN_TYPE:
        """
        获取买卖点的主类型
        返回值：'1', '2', 或 '3'（取 value 的第一个字符）
        """
        return self.value[0]  # type: ignore


class AUTYPE(Enum):
    """复权类型枚举"""
    QFQ = auto()   # 前复权（向前调整价格，默认）
    HFQ = auto()   # 后复权（向后调整价格）
    NONE = auto()  # 不复权


class TREND_TYPE(Enum):
    """趋势指标类型枚举"""
    MEAN = "mean"  # 均值（均线）
    MAX = "max"    # 最大值（上轨）
    MIN = "min"    # 最小值（下轨）


class TREND_LINE_SIDE(Enum):
    """趋势线方向枚举"""
    INSIDE = auto()   # 内部趋势线（连接笔的起点）
    OUTSIDE = auto()  # 外部趋势线（连接笔的终点）


class LEFT_SEG_METHOD(Enum):
    """尾部虚段处理方法枚举"""
    ALL = auto()   # 收集所有剩余笔为一段
    PEAK = auto()  # 寻找新的极值点形成新段


class FX_CHECK_METHOD(Enum):
    """分型检查方法枚举 - 控制笔的顶底分型合法性检查严格程度"""
    STRICT = auto()   # 严格：底分型三元素最低点必须低于顶分型三元素最低点
    LOSS = auto()     # 宽松：只比较顶底分型的中间元素
    HALF = auto()     # 半严格：比较顶分型前两元素和底分型后两元素
    TOTALLY = auto()  # 最严格：底分型最高点必须低于顶分型最低点


class SEG_TYPE(Enum):
    """线段计算级别枚举"""
    BI = auto()   # 笔级别线段（由笔构成线段）
    SEG = auto()  # 线段级别线段（由线段构成线段，即线段的线段/segseg）


class MACD_ALGO(Enum):
    """背驰判断指标算法枚举 - 用于比较两笔的力度"""
    AREA = auto()         # MACD面积（红绿柱的面积总和）
    PEAK = auto()         # MACD峰值（红绿柱的最高点，默认）
    FULL_AREA = auto()     # MACD完整面积（不考虑红绿柱颜色）
    DIFF = auto()         # MACD差值（首尾K线MACD柱子高度差）
    SLOPE = auto()         # 笔斜率（价格变化率）
    AMP = auto()           # 笔振幅（涨跌幅）
    VOLUMN = auto()        # 成交量总和
    AMOUNT = auto()         # 成交额总和
    VOLUMN_AVG = auto()     # 平均成交量
    AMOUNT_AVG = auto()     # 平均成交额
    TURNRATE_AVG = auto()   # 平均换手率
    RSI = auto()           # RSI指标极值


class DATA_FIELD:
    """
    K线数据字段名常量类
    Java 对比：类似于 Java 中定义 public static final String 常量
    注意：Python 中没有 interface 和 static final 的概念，这里直接使用类属性
    """
    FIELD_TIME = "time_key"           # 时间字段
    FIELD_OPEN = "open"               # 开盘价
    FIELD_HIGH = "high"               # 最高价
    FIELD_LOW = "low"                 # 最低价
    FIELD_CLOSE = "close"             # 收盘价
    FIELD_VOLUME = "volume"           # 成交量
    FIELD_TURNOVER = "turnover"       # 成交额
    FIELD_TURNRATE = "turnover_rate"  # 换手率


# 交易指标列表 - 用于遍历所有可选指标
# Python 的列表推导式，类似于 Java 的 List.of(...)
TRADE_INFO_LST = [DATA_FIELD.FIELD_VOLUME, DATA_FIELD.FIELD_TURNOVER, DATA_FIELD.FIELD_TURNRATE]