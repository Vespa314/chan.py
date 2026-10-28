# -*- coding: utf-8 -*-
"""
交易信息类 - 存储 K 线的扩展指标数据

Java 开发者注意：
- Dict[str, Optional[float]] 中的 Optional 类似于 Java 的 @Nullable 或 Optional<Float>
- 这个类相当于一个简单的 POJO/DTO，Python 不需要写 getter/setter
"""

from typing import Dict, Optional

from Common.CEnum import TRADE_INFO_LST


class CTradeInfo:
    """
    交易信息类，存储成交量、成交额、换手率等可选指标
    这些指标不是所有数据源都提供，所以用 Optional 包装
    """

    def __init__(self, info: Dict[str, float]):
        """
        初始化交易信息
        参数:
            info: 包含指标的字典，key 为 DATA_FIELD 常量，value 为指标值
        行为:
            只取 TRADE_INFO_LST 中定义的三个指标，未提供的设为 None
        Python 特性：dict.get(key) 如果 key 不存在返回 None，类似于 Java 的 Map.getOrDefault(key, null)
        """
        self.metric: Dict[str, Optional[float]] = {}
        for metric_name in TRADE_INFO_LST:
            self.metric[metric_name] = info.get(metric_name)

    def __str__(self):
        """
        字符串表示，格式如 "volume:100000 turnover:500000 turnover_rate:0.05"
        Python 特性：f-string 内的 for 循环，类似于 Java 中 String.join + Stream
        Python 语法：f"{k}:{v}" 是 f-string，类似于 Java 的 String.format("%s:%s", k, v)
        """
        return " ".join([f"{metric_name}:{value}" for metric_name, value in self.metric.items()])