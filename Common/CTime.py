# -*- coding: utf-8 -*-
"""
缠论时间类 - 处理不同级别 K 线的时间对齐问题

Java 开发者注意：
- Python 的 "魔术方法" __gt__, __ge__ 类似于 Java 的 Comparable 接口的 compareTo()
- __str__ 类似于 Java 的 toString()
- Python 没有方法重载，无法像 Java 那样写多个构造函数，需要用默认参数模拟
- 参数前面的 self 是 Python 要求的方法第一个参数，类似于 Java 的 this（但必须显式声明）
"""

from datetime import datetime


class CTime:
    """
    缠论时间类，封装年/月/日/时/分/秒，支持跨级别时间比较

    核心设计：auto 参数控制日线时间对齐
    - 日线数据通常不包含具体时分秒（或为 00:00:00）
    - 分钟线数据包含具体时分秒（如 10:30, 14:00）
    - 当 auto=True 时，自动将 00:00:00 的时间调整为 23:59:59
    - 这样可以确保日线 > 其下所有分钟线（因为日线代表"当天结束"）
    """

    def __init__(self, year, month, day, hour, minute, second=0, auto=True):
        """
        构造时间对象
        参数:
            year/month/day/hour/minute/second: 年月日时分秒
            auto: 是否自动调整日线时间（默认 True）
                  - True: 时分秒为 0 时自动设为 23:59，用于日线对齐
                  - False: 不做调整，用于数字货币等分钟线也可能出现 0:00 的场景
        Java 对比：Python 没有方法重载，所有参数通过默认值实现可选参数
        """
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.auto = auto  # 自适应对天的理解
        self.set_timestamp()  # 初始化时计算时间戳
        # Python 特性：不需要像 Java 那样先声明属性再赋值，直接赋值即可创建属性

    def __str__(self):
        """
        字符串表示（类似 Java 的 toString()）
        如果时间为 0:00（日线），只显示日期；否则显示日期+时间
        """
        if self.hour == 0 and self.minute == 0:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        else:
            return f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}"

    def to_str(self):
        """转换为字符串，与 __str__ 相同，提供显式调用方式"""
        if self.hour == 0 and self.minute == 0:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        else:
            return f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}"

    def toDateStr(self, splt=''):
        """
        转换为纯日期字符串
        参数:
            splt: 分隔符，默认为空字符串
        返回:
            如 '20240101'（splt=''）或 '2024-01-01'（splt='-'）
        """
        return f"{self.year:04}{splt}{self.month:02}{splt}{self.day:02}"

    def toDate(self):
        """
        获取日期部分（时分秒归零），返回一个新的 CTime 对象
        auto=False 确保不会再次被自动调整为 23:59
        """
        return CTime(self.year, self.month, self.day, 0, 0, auto=False)

    def set_timestamp(self):
        """
        设置时间戳
        核心逻辑：当 auto=True 且时分秒均为 0 时，将时间戳设为当天 23:59
        这确保了日线的时间戳 > 其下所有分钟线的时间戳
        """
        if self.hour == 0 and self.minute == 0 and self.auto:
            # 日线：自动调整为当天 23:59
            date = datetime(self.year, self.month, self.day, 23, 59, self.second)
        else:
            # 分钟线：使用实际时间
            date = datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)
        self.ts = date.timestamp()
        # Python 特性：datetime.timestamp() 返回 Unix 时间戳（float 类型）

    def __gt__(self, t2):
        """
        大于比较运算符重载（>）
        Java 对比：类似于实现 Comparable<CTime> 接口的 compareTo() 方法
        用于 K 线时间排序，确保 K 线按时间顺序处理
        """
        return self.ts > t2.ts

    def __ge__(self, t2):
        """
        大于等于比较运算符重载（>=）
        """
        return self.ts >= t2.ts