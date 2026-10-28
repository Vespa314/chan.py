# -*- coding: utf-8 -*-
"""
特征模型模块 - 存储分析过程中产生的各种特征值

Java 开发者注意：
- Python 的 dict(initFeat) 是字典构造函数，类似于 Java 的 new HashMap<>(initFeat)
- Python 的 yield from 是生成器委托语法，类似于 Java Stream 的 flatMap
- Python 的 Optional[float] 是类型提示，表示值可能是 float 或 None
  Java 对比：类似于 Java 的 @Nullable Float 或 Optional<Float>
- Python 的 __getitem__ 是魔法方法，实现 obj[k] 语法
  Java 对比：类似于实现 Map 接口的 get 方法，但通过 [] 而非 .get() 调用
"""

from typing import Optional


class CFeatures:
    """
    特征存储容器 - 键值对存储，支持合并和迭代

    用于存储分析过程中产生的各种特征值（如 MACD、RSI 等指标值），
    这些特征值会被后续的买卖点判断等逻辑使用。

    参数:
        initFeat: 可选初始化字典，用于导入已有特征

    使用示例:
        feat = CFeatures({"macd": 0.5, "rsi": 60})
        feat.add_feat("kdj", 80)
        for k, v in feat.items():
            print(k, v)
    """

    def __init__(self, initFeat=None):
        # dict() 创建新字典，避免引用外部可变对象
        # Java 对比：new HashMap<>(initFeat) 而不是直接赋值引用
        self.__features = {} if initFeat is None else dict(initFeat)

    def items(self):
        """
        迭代所有特征项的 (key, value) 对

        yield from 将迭代委托给内部字典的 items() 方法
        Java 对比：类似于返回 Map.entrySet().iterator() 的包装器
        """
        yield from self.__features.items()

    def __getitem__(self, k):
        """
        通过 key 获取特征值，支持 obj[k] 语法

        Java 对比：类似于 Map.get(k)，但 Python 通过 [] 访问
        """
        return self.__features[k]

    def add_feat(self, inp1, inp2: Optional[float] = None):
        """
        添加特征值

        参数:
            inp1: 可以是字典（批量添加）或字符串（单个 key）
            inp2: 当 inp1 是字符串时的值，Optional 表示可为 None

        支持两种调用方式：
        - add_feat({"key": value}) → 批量添加
        - add_feat("key", value) → 单个添加

        Python 特性：参数类型根据 inp2 是否为 None 来判断 inp1 是字典还是 key
        Java 对比：Java 需要方法重载 addFeat(Map) 和 addFeat(String, Float)
        """
        if inp2 is None:
            # inp1 是字典，批量更新
            self.__features.update(inp1)
        else:
            # inp1 是 key，inp2 是 value
            self.__features.update({inp1: inp2})