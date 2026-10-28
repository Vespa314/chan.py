# -*- coding: utf-8 -*-
"""
缓存装饰器模块 - 提供方法级别的备忘录缓存

Java 开发者注意：
- Python 装饰器类似于 Java 的 AOP（面向切面编程）或代理模式
- @make_cache 放在方法前面，相当于自动为该方法添加缓存逻辑
- 这是 Python 的"描述器协议"（Descriptor Protocol），类似于 Java 的反射+动态代理
- types.MethodType 类似于 Java 的 MethodHandle 或反射中的 Method 绑定

工作原理：
1. 当访问 instance.method() 时，Python 调用 __get__ 获取绑定方法
2. __get__ 创建 MethodType 绑定 self 和 make_cache 实例
3. 调用时进入 __call__，先查缓存，未命中则执行原方法并缓存结果
"""

import inspect
import types


class make_cache:
    """
    实例方法级别的缓存装饰器
    使用方式：在方法前加 @make_cache
    Python 语法：装饰器实质上是语法糖，@make_cache 等价于 method = make_cache(method)

    缓存存储位置：self._memoize_cache（字典）
    缓存 key：函数名（str(func)）
    缓存失效：调用 clean_cache() 清空整个 _memoize_cache 字典
    """

    def __init__(self, func):
        """
        初始化装饰器，保存原函数引用
        参数:
            func: 被装饰的函数对象
        Python 特性：inspect 模块用于内省，类似于 Java 的反射
        """
        self.func = func

        # 检查被装饰函数的签名，确保只有 (self) 一个参数
        # Python 特性：inspect.getfullargspec() 获取函数的完整参数信息
        # Java 对比：类似于 Java 反射中的 Method.getParameters()
        fargspec = inspect.getfullargspec(func)
        if len(fargspec.args) != 1 or fargspec.args[0] != "self":
            raise Exception("@memoize must be `(self)`")

        # 设置缓存 key（使用函数字符串表示）
        # Python 特性：str(func) 返回函数的内存地址标识，确保每个方法有唯一的 key
        self.func_key = str(func)

    def __get__(self, instance, cls):
        """
        描述器协议方法：当通过实例访问被装饰的方法时调用
        参数:
            instance: 方法所属的实例（如果通过类访问则为 None）
            cls: 方法所属的类
        返回:
            绑定到实例的 MethodType 对象
        Java 对比：类似于动态代理中的 InvocationHandler.invoke() 中的 Method
        """
        if instance is None:
            raise Exception("@memoize's must be bound")

        # 为每个实例创建独立的缓存字典（如果还没有的话）
        # Python 特性：hasattr/setattr 类似于 Java 反射中的 getField/setField
        if not hasattr(instance, "_memoize_cache"):
            setattr(instance, "_memoize_cache", {})

        # 返回绑定到实例的方法对象
        # Python 特性：types.MethodType 将函数绑定到实例，类似于 Java 中 Method.invoke(obj, args)
        return types.MethodType(self, instance)

    def __call__(self, *args, **kwargs):
        """
        缓存查找逻辑：命中缓存返回缓存值，未命中执行原函数并缓存
        参数:
            *args: 位置参数（Python 的变长参数，类似于 Java 的 Object...）
            **kwargs: 关键字参数（Python 特有的，类似于 Java 的 Map）
        返回:
            原函数的返回值
        Python 特性：*args 和 **kwargs 是 Python 特有的，Java 没有直接对应的语法
        """
        instance = args[0]  # 取 self
        cache = instance._memoize_cache

        # 查缓存
        if self.func_key in cache:
            return cache[self.func_key]

        # 缓存未命中，执行原函数并缓存结果
        result = self.func(*args, **kwargs)
        cache[self.func_key] = result
        return result