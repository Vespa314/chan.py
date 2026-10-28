# -*- coding: utf-8 -*-
"""
主入口模块 - 缠论分析引擎的核心调度类

Java 开发者注意：
- Python 的 if cond: ... 单行语法，类似于 Java 的单行 if 语句
- Python 的 isinstance(obj, datetime.date) 检查对象类型
  Java 对比：obj instanceof java.time.LocalDate
- Python 的 defaultdict 是带默认值的字典，访问不存在的键时自动创建默认值
  Java 对比：类似于 HashMap + computeIfAbsent
- Python 的 hasattr(obj, 'attr') 检查对象是否有某个属性
  Java 对比：类似于反射中的 obj.getClass().getDeclaredField("attr") != null
- Python 字符串拼接 f"..." 是 f-string（格式化字符串字面量）
  Java 对比：类似于 Java 的 String.format() 或 $"..." 文本块
- Python 的 __getitem__ 实现 obj[n] 语法，类似于 Java 的 List.get(n) 或 Map.get(key)
- Python 的 __deepcopy__ 实现深度拷贝协议，类似于 Java 的 Cloneable.clone()
- Python 的 @staticmethod 静态方法，类似于 Java 的 static 方法
- Python 的 sys.setrecursionlimit(0x100000) 设置递归深度限制
  Java 对比：Java 的递归深度由栈大小决定，不能运行时动态调整
- Python 的 yield from 是生成器委托，将迭代委托给另一个生成器
  Java 对比：Java 没有 yield，需要手动实现迭代器
- Python 的 try/except/else/finally 比 Java 多一个 else 分支
  else 在 try 块未抛出异常时执行
- Python 的 for _ in iterator: ... 中 _ 表示不使用循环变量
  Java 对比：Java 没有这种约定，通常直接忽略
- Python 的 importlib.import_module 动态导入模块，类似于 Java 的 Class.forName
- Python 的 getattr(obj, 'attr_name') 按名称获取属性，类似于 Java 反射的 Field.get
"""

import copy
import datetime
import pickle
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Union

from BuySellPoint.BS_Point import CBS_Point
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import check_kltype_order, kltype_lte_day
from DataAPI.CommonStockAPI import CCommonStockApi
from KLine.KLine_List import CKLine_List
from KLine.KLine_Unit import CKLine_Unit


class CChan:
    """
    缠论分析引擎 - 主入口类

    负责：
    1. 管理多级别K线数据加载
    2. 递归加载子级别K线
    3. 数据完整性校验
    4. 触发各级别的分析计算
    5. 序列化/反序列化

    参数:
        code: 股票/交易品种代码
        begin_time: 数据起始时间
        end_time: 数据结束时间
        data_src: 数据源类型（BAO_STOCK/CCXT/CSV/AKSHARE/自定义）
        lv_list: 级别列表（从高到低，如 [K_DAY, K_60M]）
        config: 配置对象
        autype: 复权类型（QFQ=前复权, HFQ=后复权, NONE=不复权）

    缠论知识 - 多级别联立分析：
    缠论强调多级别联立分析，高级别的笔/线段由低级别递归构成。
    例如：日线的一笔 → 60分钟的一段 → 15分钟的一段 → ...
    通过递归加载子级别数据，实现从高级别到低级别的完整分析。
    """

    def __init__(
        self,
        code,
        begin_time=None,
        end_time=None,
        data_src: Union[DATA_SRC, str] = DATA_SRC.BAO_STOCK,
        lv_list=None,
        config=None,
        autype: AUTYPE = AUTYPE.QFQ,
    ):
        if lv_list is None:
            lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_60M]  # 默认日线+60分钟线
        check_kltype_order(lv_list)  # 确保 lv_list 顺序从高到低
        self.code = code
        # Python 特性：isinstance 检查 + 三元表达式的行内转换
        self.begin_time = str(begin_time) if isinstance(begin_time, datetime.date) else begin_time
        self.end_time = str(end_time) if isinstance(end_time, datetime.date) else end_time
        self.autype = autype
        self.data_src = data_src
        self.lv_list: List[KL_TYPE] = lv_list

        if config is None:
            config = CChanConfig()
        self.conf = config

        # 数据校验计数器
        self.kl_misalign_cnt = 0                          # 子级别K线缺失计数
        self.kl_inconsistent_detail = defaultdict(list)    # 时间不一致详情

        # 全局K线迭代器存储
        self.g_kl_iter = defaultdict(list)

        self.do_init()

        # 如果非步进模式，一次性加载所有数据
        if not config.trigger_step:
            for _ in self.load():
                ...

    def __deepcopy__(self, memo):
        """
        深度拷贝实现

        参数:
            memo: Python 的拷贝记忆字典，用于处理循环引用

        返回:
            深度拷贝后的 CChan 对象

        Python 特性：__deepcopy__ 是 Python 的拷贝协议
        - memo 字典记录已拷贝的对象，防止无限递归
        - cls.__new__(cls) 创建未初始化的实例，类似于 Java 的 Unsafe.allocateInstance
        Java 对比：Java 的 Cloneable.clone() 只能做浅拷贝，深拷贝需要手动实现

        注意：拷贝后需要重建 sup_kl/sub_kl 的引用关系，确保引用指向正确的拷贝对象。
        """
        cls = self.__class__
        obj: CChan = cls.__new__(cls)  # 创建未初始化的实例
        memo[id(self)] = obj           # 注册到 memo，防止循环引用

        # 拷贝基本属性
        obj.code = self.code
        obj.begin_time = self.begin_time
        obj.end_time = self.end_time
        obj.autype = self.autype
        obj.data_src = self.data_src
        obj.lv_list = copy.deepcopy(self.lv_list, memo)
        obj.conf = copy.deepcopy(self.conf, memo)
        obj.kl_misalign_cnt = self.kl_misalign_cnt
        obj.kl_inconsistent_detail = copy.deepcopy(self.kl_inconsistent_detail, memo)
        obj.g_kl_iter = copy.deepcopy(self.g_kl_iter, memo)

        # 拷贝缓存（如果存在）
        if hasattr(self, 'klu_cache'):
            obj.klu_cache = copy.deepcopy(self.klu_cache, memo)
        if hasattr(self, 'klu_last_t'):
            obj.klu_last_t = copy.deepcopy(self.klu_last_t, memo)

        # 拷贝K线数据
        obj.kl_datas = {}
        for kl_type, ckline in self.kl_datas.items():
            obj.kl_datas[kl_type] = copy.deepcopy(ckline, memo)

        # 重建 sup_kl/sub_kl 引用关系
        for kl_type, ckline in self.kl_datas.items():
            for klc in ckline:
                for klu in klc.lst:
                    assert id(klu) in memo
                    if klu.sup_kl:
                        memo[id(klu)].sup_kl = memo[id(klu.sup_kl)]
                    memo[id(klu)].sub_kl_list = [memo[id(sub_kl)] for sub_kl in klu.sub_kl_list]
        return obj

    def do_init(self):
        """
        初始化各级别的K线列表

        为每个级别创建一个 CKLine_List 对象，用于存储和管理该级别的K线数据。
        """
        self.kl_datas: Dict[KL_TYPE, CKLine_List] = {}
        for idx in range(len(self.lv_list)):
            self.kl_datas[self.lv_list[idx]] = CKLine_List(self.lv_list[idx], conf=self.conf)

    def load_stock_data(self, stockapi_instance: CCommonStockApi, lv) -> Iterable[CKLine_Unit]:
        """
        加载股票数据

        参数:
            stockapi_instance: 数据源API实例
            lv: 当前级别

        返回:
            CKLine_Unit 的迭代器

        为每根K线设置索引和级别信息。
        """
        for KLU_IDX, klu in enumerate(stockapi_instance.get_kl_data()):
            klu.set_idx(KLU_IDX)
            klu.kl_type = lv
            yield klu

    def get_load_stock_iter(self, stockapi_cls, lv):
        """
        获取数据加载迭代器

        参数:
            stockapi_cls: 数据源API类
            lv: 当前级别

        返回:
            CKLine_Unit 的迭代器
        """
        stockapi_instance = stockapi_cls(
            code=self.code, k_type=lv,
            begin_date=self.begin_time, end_date=self.end_time, autype=self.autype
        )
        return self.load_stock_data(stockapi_instance, lv)

    def add_lv_iter(self, lv_idx, iter):
        """
        添加级别的K线迭代器

        参数:
            lv_idx: 级别索引（int）或级别类型（KL_TYPE）
            iter: K线数据迭代器

        支持两种传入方式：索引或级别类型。
        """
        if isinstance(lv_idx, int):
            self.g_kl_iter[self.lv_list[lv_idx]].append(iter)
        else:
            self.g_kl_iter[lv_idx].append(iter)

    def get_next_lv_klu(self, lv_idx):
        """
        获取下一个级别的K线

        参数:
            lv_idx: 级别索引或级别类型

        返回:
            下一根 CKLine_Unit

        处理逻辑：
        1. 从当前迭代器中取下一根K线
        2. 如果迭代器耗尽，切换到下一个迭代器
        3. 如果所有迭代器都耗尽，抛出 StopIteration

        Python 特性：
        - iter.__next__() 是迭代器的下一个元素
          Java 对比：iterator.next()
        - StopIteration 是 Python 迭代器结束的信号
          Java 对比：类似于 NoSuchElementException
        """
        if isinstance(lv_idx, int):
            lv_idx = self.lv_list[lv_idx]
        if len(self.g_kl_iter[lv_idx]) == 0:
            raise StopIteration
        try:
            return self.g_kl_iter[lv_idx][0].__next__()
        except StopIteration:
            # 当前迭代器耗尽，移除它
            self.g_kl_iter[lv_idx] = self.g_kl_iter[lv_idx][1:]
            if len(self.g_kl_iter[lv_idx]) != 0:
                return self.get_next_lv_klu(lv_idx)  # 递归尝试下一个迭代器
            else:
                raise

    def step_load(self):
        """
        步进加载模式（生成器）

        返回:
            每次 yield 当前状态的 CChan 对象

        用于回放模式，逐步展示分析过程。
        每加载一根K线就 yield 一次，让外部可以观察分析过程。

        如果 skip_step > 0，跳过前 N 步。
        如果从未 yield 过（数据为空），最后 yield 一次当前状态。
        """
        assert self.conf.trigger_step
        self.do_init()  # 清空数据，防止再次重跑没有数据
        yielded = False  # 是否曾经返回过结果
        for idx, snapshot in enumerate(self.load(self.conf.trigger_step)):
            if idx < self.conf.skip_step:
                continue
            yield snapshot
            yielded = True
        if not yielded:
            yield self

    def trigger_load(self, inp):
        """
        触发加载模式 - 从外部传入数据

        参数:
            inp: {级别类型: [K线列表]} 的字典

        用于外部逐条推送K线数据的场景，比自动加载更灵活。
        处理流程：
        1. 初始化缓存
        2. 按级别添加迭代器
        3. 调用 load_iterator 处理
        4. 非步进模式下计算线段和中枢
        """
        # 初始化缓存
        if not hasattr(self, 'klu_cache'):
            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
        if not hasattr(self, 'klu_last_t'):
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]

        for lv_idx, lv in enumerate(self.lv_list):
            if lv not in inp:
                if lv_idx == 0:
                    raise CChanException(f"最高级别{lv}没有传入数据", ErrCode.NO_DATA)
                continue
            for klu in inp[lv]:
                klu.kl_type = lv
            assert isinstance(inp[lv], list)
            self.add_lv_iter(lv, iter(inp[lv]))

        for _ in self.load_iterator(lv_idx=0, parent_klu=None, step=False):
            ...

        if not self.conf.trigger_step:  # 非回放模式全部算完之后才算一次中枢和线段
            for lv in self.lv_list:
                self.kl_datas[lv].cal_seg_and_zs()

    def init_lv_klu_iter(self, stockapi_cls):
        """
        初始化各级别的K线迭代器

        参数:
            stockapi_cls: 数据源API类

        返回:
            [(lv, iterator), ...] 列表

        处理逻辑：
        1. 遍历所有级别，尝试获取数据
        2. 如果某个级别获取失败且 auto_skip_illegal_sub_lv=True，跳过该级别
        3. 否则抛出异常
        """
        lv_klu_iter = []
        valid_lv_list = []
        for lv in self.lv_list:
            try:
                lv_klu_iter.append(self.get_load_stock_iter(stockapi_cls, lv))
                valid_lv_list.append(lv)
            except CChanException as e:
                if e.errcode == ErrCode.SRC_DATA_NOT_FOUND and self.conf.auto_skip_illegal_sub_lv:
                    if self.conf.print_warning:
                        print(f"[WARNING-{self.code}]{lv}级别获取数据失败，跳过")
                    del self.kl_datas[lv]
                    continue
                raise e
        self.lv_list = valid_lv_list
        return lv_klu_iter

    def GetStockAPI(self):
        """
        根据数据源类型获取对应的 API 类

        返回:
            数据源 API 类

        支持的数据源：
        - BAO_STOCK: BaoStock API
        - CCXT: 加密货币数据
        - CSV: 本地 CSV 文件
        - AKSHARE: Akshare API
        - custom:XX.YY: 自定义数据源（动态导入）

        Python 特性：延迟导入（lazy import）
        - 在函数内部 import 模块，只在需要时加载
        - 避免全局导入不必要的依赖
        Java 对比：Java 的类加载是惰性的（默认在第一次使用时加载类）
        """
        _dict = {}
        if self.data_src == DATA_SRC.BAO_STOCK:
            from DataAPI.BaoStockAPI import CBaoStock
            _dict[DATA_SRC.BAO_STOCK] = CBaoStock
        elif self.data_src == DATA_SRC.CCXT:
            from DataAPI.ccxt import CCXT
            _dict[DATA_SRC.CCXT] = CCXT
        elif self.data_src == DATA_SRC.CSV:
            from DataAPI.csvAPI import CSV_API
            _dict[DATA_SRC.CSV] = CSV_API
        elif self.data_src == DATA_SRC.AKSHARE:
            from DataAPI.AkshareAPI import CAkshare
            _dict[DATA_SRC.AKSHARE] = CAkshare

        if self.data_src in _dict:
            return _dict[self.data_src]

        # 自定义数据源：格式 "custom:package_name.ClassName"
        assert isinstance(self.data_src, str)
        if self.data_src.find("custom:") < 0:
            raise CChanException("load src type error", ErrCode.SRC_DATA_TYPE_ERR)
        package_info = self.data_src.split(":")[1]
        package_name, cls_name = package_info.split(".")
        import importlib
        module = importlib.import_module(f"DataAPI.{package_name}")
        return getattr(module, cls_name)

    def load(self, step=False):
        """
        主加载方法 - 加载所有级别的K线数据

        参数:
            step: 是否步进模式（True=每根K线yield一次）

        返回:
            CChan 对象的迭代器（步进模式）或完成加载（非步进模式）

        处理流程：
        1. 获取数据源API类
        2. 初始化数据源
        3. 为每个级别创建K线迭代器
        4. 递归加载所有级别的数据
        5. 非步进模式下计算线段和中枢
        6. 校验数据有效性

        Python 特性：
        - try/except/finally 结构，finally 确保 do_close() 一定执行
        - yield from 委托给 load_iterator 生成器
        """
        stockapi_cls = self.GetStockAPI()
        try:
            stockapi_cls.do_init()
            # 为每个级别创建K线迭代器
            for lv_idx, klu_iter in enumerate(self.init_lv_klu_iter(stockapi_cls)):
                self.add_lv_iter(lv_idx, klu_iter)

            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]

            # 计算入口：递归加载各级别数据
            yield from self.load_iterator(lv_idx=0, parent_klu=None, step=step)

            if not step:  # 非回放模式全部算完之后才算一次中枢和线段
                for lv in self.lv_list:
                    self.kl_datas[lv].cal_seg_and_zs()
        except Exception:
            raise
        finally:
            stockapi_cls.do_close()  # 无论是否异常，都确保关闭数据源

        if len(self[0]) == 0:
            raise CChanException("最高级别没有获得任何数据", ErrCode.NO_DATA)

    def set_klu_parent_relation(self, parent_klu, kline_unit, cur_lv, lv_idx):
        """
        设置父子K线关系

        参数:
            parent_klu: 父级别K线
            kline_unit: 当前子级别K线
            cur_lv: 当前级别
            lv_idx: 当前级别索引

        建立高级别K线与低级别K线之间的父子关系，
        同时进行数据一致性校验。
        """
        if self.conf.kl_data_check and kltype_lte_day(cur_lv) and kltype_lte_day(self.lv_list[lv_idx - 1]):
            self.check_kl_consitent(parent_klu, kline_unit)
        parent_klu.add_children(kline_unit)
        kline_unit.set_parent(parent_klu)

    def add_new_kl(self, cur_lv: KL_TYPE, kline_unit):
        """
        添加新K线到对应级别的K线列表

        参数:
            cur_lv: 当前级别
            kline_unit: K线单元

        调用 CKLine_List.add_single_klu() 进行K线包含处理。
        如果处理失败，根据配置决定是否打印错误信息。
        """
        try:
            self.kl_datas[cur_lv].add_single_klu(kline_unit)
        except Exception:
            if self.conf.print_err_time:
                print(f"[ERROR-{self.code}]在计算{kline_unit.time}K线时发生错误!")
            raise

    def try_set_klu_idx(self, lv_idx: int, kline_unit: CKLine_Unit):
        """
        设置K线索引

        参数:
            lv_idx: 级别索引
            kline_unit: K线单元

        如果K线已有索引，不重复设置。
        如果该级别还没有K线，从0开始。
        否则从最后一根K线的索引+1。
        """
        if kline_unit.idx >= 0:
            return
        if len(self[lv_idx]) == 0:
            kline_unit.set_idx(0)
        else:
            kline_unit.set_idx(self[lv_idx][-1][-1].idx + 1)

    def load_iterator(self, lv_idx, parent_klu, step):
        """
        递归加载K线迭代器 - 核心加载逻辑

        参数:
            lv_idx: 当前级别索引
            parent_klu: 父级别K线（None表示最高级别）
            step: 是否步进模式

        返回:
            CChan 对象的迭代器（步进模式）

        核心递归逻辑：
        1. 从当前级别获取下一根K线
        2. 校验时间单调性
        3. 如果K线时间 > 父K线时间 → 缓存并返回（等待父K线前进）
        4. 设置前后K线关系
        5. 添加到当前级别K线列表
        6. 设置父子关系
        7. 递归加载子级别数据
        8. 校验子级别数据对齐

        缠论知识 - 递归加载：
        这是多级别联立分析的核心。
        从最高级别开始，为每根高级别K线递归加载其包含的所有低级别K线。
        例如：日线K线 → 60分钟K线 → 15分钟K线 → 5分钟K线

        时间比较规则：
        K线时间天级别以下描述的是结束时间，如60M线每天第一根是10:30的。
        天以上是当天日期。
        """
        # K线时间天级别以下描述的是结束时间，如60M线，每天第一根是10点30的
        # 天以上是当天日期
        cur_lv = self.lv_list[lv_idx]
        pre_klu = self[lv_idx][-1][-1] if len(self[lv_idx]) > 0 and len(self[lv_idx][-1]) > 0 else None

        while True:
            # 先检查缓存中是否有待处理的K线
            if self.klu_cache[lv_idx]:
                kline_unit = self.klu_cache[lv_idx]
                assert kline_unit is not None
                self.klu_cache[lv_idx] = None
            else:
                try:
                    kline_unit = self.get_next_lv_klu(lv_idx)
                    self.try_set_klu_idx(lv_idx, kline_unit)

                    # 时间单调性校验
                    if not kline_unit.time > self.klu_last_t[lv_idx]:
                        raise CChanException(
                            f"kline time err, cur={kline_unit.time}, last={self.klu_last_t[lv_idx]}, "
                            f"or refer to quick_guide.md, "
                            f"try set auto=False in the CTime returned by your data source class",
                            ErrCode.KL_NOT_MONOTONOUS
                        )
                    self.klu_last_t[lv_idx] = kline_unit.time
                except StopIteration:
                    break  # 该级别数据已全部加载

            # 如果子K线时间超过父K线时间 → 缓存当前K线，等待父K线前进
            if parent_klu and kline_unit.time > parent_klu.time:
                self.klu_cache[lv_idx] = kline_unit
                break

            # 设置前后K线关系（双向链表）
            kline_unit.set_pre_klu(pre_klu)
            pre_klu = kline_unit

            # 添加K线到当前级别
            self.add_new_kl(cur_lv, kline_unit)

            # 设置父子K线关系
            if parent_klu:
                self.set_klu_parent_relation(parent_klu, kline_unit, cur_lv, lv_idx)

            # 递归加载子级别数据
            if lv_idx != len(self.lv_list) - 1:
                for _ in self.load_iterator(lv_idx + 1, kline_unit, step):
                    ...
                self.check_kl_align(kline_unit, lv_idx)

            # 步进模式：每完成一根最高级别K线就 yield 一次
            if lv_idx == 0 and step:
                yield self

    def check_kl_consitent(self, parent_klu, sub_klu):
        """
        检查父子K线时间一致性

        参数:
            parent_klu: 父级别K线
            sub_klu: 子级别K线

        检查父子K线是否属于同一天。
        如果时间不一致次数超过阈值，抛出异常。
        这只在天级别及以下级别检查（分钟线等）。
        """
        if parent_klu.time.year != sub_klu.time.year or \
           parent_klu.time.month != sub_klu.time.month or \
           parent_klu.time.day != sub_klu.time.day:
            self.kl_inconsistent_detail[str(parent_klu.time)].append(sub_klu.time)
            if self.conf.print_warning:
                print(f"[WARNING-{self.code}]父级别时间是{parent_klu.time}，次级别时间却是{sub_klu.time}")
            if len(self.kl_inconsistent_detail) >= self.conf.max_kl_inconsistent_cnt:
                raise CChanException(
                    f"父&子级别K线时间不一致条数超过{self.conf.max_kl_inconsistent_cnt}！！",
                    ErrCode.KL_TIME_INCONSISTENT
                )

    def check_kl_align(self, kline_unit, lv_idx):
        """
        检查子级别K线数据对齐

        参数:
            kline_unit: 当前级别K线
            lv_idx: 当前级别索引

        如果开启了数据校验，检查当前K线是否在子级别找到了对应的K线。
        如果缺失次数超过阈值，抛出异常。
        """
        if self.conf.kl_data_check and len(kline_unit.sub_kl_list) == 0:
            self.kl_misalign_cnt += 1
            if self.conf.print_warning:
                print(f"[WARNING-{self.code}]当前{kline_unit.time}没在次级别{self.lv_list[lv_idx + 1]}找到K线！！")
            if self.kl_misalign_cnt >= self.conf.max_kl_misalgin_cnt:
                raise CChanException(
                    f"在次级别找不到K线条数超过{self.conf.max_kl_misalgin_cnt}！！",
                    ErrCode.KL_DATA_NOT_ALIGN
                )

    def __getitem__(self, n) -> CKLine_List:
        """
        获取指定级别的 KLine_List

        支持两种索引方式：
        - 按级别类型：chan[KL_TYPE.K_DAY]
        - 按索引：chan[0] 获取最高级别

        Python 特性：__getitem__ 实现 [] 运算符
        Java 对比：类似于实现 Map 接口的 get 方法
        """
        if isinstance(n, KL_TYPE):
            return self.kl_datas[n]
        elif isinstance(n, int):
            return self.kl_datas[self.lv_list[n]]
        else:
            raise CChanException("unspoourt query type", ErrCode.COMMON_ERROR)

    def get_bsp(self, idx=None) -> List[CBS_Point]:
        """
        获取买卖点列表（已废弃）

        Python 特性：[] 切片语法
        - self[idx] 实际上调用了 __getitem__(idx)
        """
        print('[deprecated] use get_latest_bsp instead')
        if idx is not None:
            return self[idx].bs_point_lst.getSortedBspList()
        assert len(self.lv_list) == 1
        return self[0].bs_point_lst.getSortedBspList()

    def get_latest_bsp(self, idx=None, number=1) -> List[CBS_Point]:
        """
        获取最新的买卖点列表

        参数:
            idx: 级别索引或类型
            number: 获取数量（0=全部，从最新到最旧排序）

        返回:
            CBS_Point 列表
        """
        if idx is not None:
            return self[idx].bs_point_lst.get_latest_bsp(number)
        assert len(self.lv_list) == 1
        return self[0].bs_point_lst.get_latest_bsp(number)

    def chan_dump_pickle(self, file_path):
        """
        序列化保存 chan 对象到 pickle 文件

        参数:
            file_path: 保存路径

        保存前清理双向引用（pre/next），避免循环引用导致序列化失败。
        保存后恢复双向引用。

        Python 特性：
        - sys.setrecursionlimit(0x100000) 提高递归深度限制
          pickle 序列化复杂对象结构可能需要更深的递归栈
        """
        _pre_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(0x100000)  # 增大递归深度，支持复杂对象序列化

        # 清理双向引用，避免循环引用
        for kl_list in self.kl_datas.values():
            for klc in kl_list.lst:
                for klu in klc.lst:
                    klu.pre = None
                    klu.next = None
                klc.set_pre(None)
                klc.set_next(None)
            for bi in kl_list.bi_list:
                bi.pre = None
                bi.next = None
            for seg in kl_list.seg_list:
                seg.pre = None
                seg.next = None
            for segseg in kl_list.segseg_list:
                segseg.pre = None
                segseg.next = None

        with open(file_path, "wb") as f:
            pickle.dump(self, f)

        sys.setrecursionlimit(_pre_limit)
        self.chan_pickle_restore()  # 恢复双向引用

    @staticmethod
    def chan_load_pickle(file_path) -> 'CChan':
        """
        从 pickle 文件加载 chan 对象

        参数:
            file_path: pickle 文件路径

        返回:
            恢复后的 CChan 对象

        Python 特性：@staticmethod 是静态方法，不需要 self 参数
        Java 对比：类似于 public static CChan loadFromFile(String path)
        """
        with open(file_path, "rb") as f:
            chan = pickle.load(f)
        chan.chan_pickle_restore()  # 恢复双向引用
        return chan

    def chan_pickle_restore(self):
        """
        恢复 pickle 后的双向引用关系

        由于 pickle 序列化时清除了 pre/next 双向引用，
        加载后需要重新建立这些引用关系。
        遍历各级别的 K线、笔、线段、线段线段，重建双向链表。
        """
        for kl_list in self.kl_datas.values():
            last_klu = None
            last_klc = None
            last_bi = None
            last_seg = None
            last_segseg = None

            # 恢复 K 线链表
            for klc in kl_list.lst:
                for klu in klc.lst:
                    klu.pre = last_klu
                    if last_klu:
                        last_klu.next = klu
                    last_klu = klu
                klc.set_pre(last_klc)
                if last_klc:
                    last_klc.set_next(klc)
                last_klc = klc

            # 恢复笔链表
            for bi in kl_list.bi_list:
                bi.pre = last_bi
                if last_bi:
                    last_bi.next = bi
                last_bi = bi

            # 恢复线段链表
            for seg in kl_list.seg_list:
                seg.pre = last_seg
                if last_seg:
                    last_seg.next = seg
                last_seg = seg

            # 恢复线段线段链表
            for segseg in kl_list.segseg_list:
                segseg.pre = last_segseg
                if last_segseg:
                    last_segseg.next = segseg
                last_segseg = segseg