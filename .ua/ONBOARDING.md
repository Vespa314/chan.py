# chan.py 开发者入职指南

> 自动生成于 2026-09-05 | 基于知识图谱分析 | 73 个文件 · 223 个节点 · 651 条边

---

## 项目概述

**chan.py** 是缠论（Chan Theory）技术分析的 Python 实现框架，用于从 K 线数据计算分形、笔、线段、中枢、买卖点等缠论基本元素，支持多级别联立计算、区间套、多种数据源适配及 matplotlib 可视化绘图。

| 属性 | 值 |
|------|-----|
| 语言 | Python ≥ 3.11 |
| 框架 | 无（纯 Python 计算库） |
| 协议 | MIT |
| 作者 | Vespa314 |
| 文件总数 | 73（65 代码 + 7 文档 + 1 配置） |
| 代码行数 | ~5300（开源版） |

---

## 架构层次

项目分为 8 个架构层，从底层基础到上层应用：

```
┌─────────────────────────────────────────────────┐
│              演示与测试层 (6)                      │
│   strategy_demo / strategy_demo2~6               │
├─────────────────────────────────────────────────┤
│  入口/门面层 (5)         可视化层 (4)              │
│  CChan / CChanConfig     PlotDriver / Animate    │
├─────────────────────────────────────────────────┤
│              缠论核心计算层 (29)                   │
│  Combiner → KLine → Bi → Seg → ZS → BuySellPoint │
├──────────────────┬──────────────────────────────┤
│  技术指标层 (8)    │  数据适配层 (6)               │
│  MACD/BOLL/RSI…  │  BaoStock/Akshare/CCXT/CSV   │
├──────────────────┴──────────────────────────────┤
│              基础公共层 (6)                        │
│  CEnum / ChanException / cache / CTime / func_util│
├─────────────────────────────────────────────────┤
│              文档与配置层 (9)                      │
│  README / 快速指南 / 代码走读 / 依赖清单           │
└─────────────────────────────────────────────────┘
```

### 1. 基础公共层（6 文件）

项目级基础设施，fan-in 最高（被所有其他层依赖）。

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Common/CEnum.py](Common/CEnum.py) | 🟡 moderate | 15 个核心枚举类：K线级别、方向、分形类型、笔类型、买卖点类型、MACD算法等 |
| [Common/ChanException.py](Common/ChanException.py) | 🟡 moderate | 30+ 错误码的异常体系，`CChanException` 自定义异常类 |
| [Common/cache.py](Common/cache.py) | 🟡 moderate | `@make_cache` 装饰器——实例级记忆化，支持 `clean_cache()` 失效 |
| [Common/CTime.py](Common/CTime.py) | 🟡 moderate | 时间包装类，K线时间戳的统一入口 |
| [Common/func_util.py](Common/func_util.py) | 🟢 simple | 通用工具：K线周期比较、区间重叠判断、字符串转浮点数 |

### 2. 技术指标层（8 文件）

手写实现的技术指标，不依赖 talib，保证跨平台兼容性。

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Math/MACD.py](Math/MACD.py) | 🟢 simple | MACD：DIF、DEA、柱状线，支持 3 种算法 |
| [Math/BOLL.py](Math/BOLL.py) | 🟢 simple | 布林带：中轨、上轨、下轨 |
| [Math/RSI.py](Math/RSI.py) | 🟢 simple | 相对强弱指标 |
| [Math/KDJ.py](Math/KDJ.py) | 🟢 simple | KDJ 随机指标 |
| [Math/Demark.py](Math/Demark.py) | 🔴 complex | **DeMark 序列**：Setup + Countdown 两阶段引擎，TDST 压力/支撑线 |
| [Math/TrendLine.py](Math/TrendLine.py) | 🟡 moderate | 趋势线拟合：基于峰谷点的斜率计算 |
| [Math/TrendModel.py](Math/TrendModel.py) | 🟢 simple | 趋势模型：均值回归计算器 |

### 3. 数据适配层（6 文件）

适配器模式，统一接口接入多种数据源。

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [DataAPI/CommonStockAPI.py](DataAPI/CommonStockAPI.py) | 🟡 moderate | 抽象基类，定义 `get_kl_data()` 等统一接口 |
| [DataAPI/BaoStockAPI.py](DataAPI/BaoStockAPI.py) | 🟡 moderate | BaoStock A 股数据适配器（默认） |
| [DataAPI/AkshareAPI.py](DataAPI/AkshareAPI.py) | 🔴 complex | Akshare 财经数据适配器 |
| [DataAPI/ccxt.py](DataAPI/ccxt.py) | 🔴 complex | CCXT 加密货币交易所适配器 |
| [DataAPI/csvAPI.py](DataAPI/csvAPI.py) | 🟡 moderate | CSV 本地文件适配器 |

### 4. 缠论核心计算层（29 文件）

**这是项目最核心的部分**，实现从原始 K 线到缠论元素的完整递推计算流水线：

```
KLine_Unit → Combiner → KLine → Bi → Seg → ZS → BuySellPoint
  (单根K线)   (包含处理)  (合并K线) (笔)  (线段) (中枢)  (买卖点)
```

#### Combiner — K 线包含处理

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Combiner/KLine_Combiner.py](Combiner/KLine_Combiner.py) | 🔴 complex | **核心基类**：包含关系判断、合并高低点、分形检测、前后链表管理 |
| [Combiner/Combine_Item.py](Combiner/Combine_Item.py) | 🟢 simple | 适配器：统一包装 CBi/CKLine_Unit/CSeg 的接口 |

#### KLine — K 线数据结构

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [KLine/KLine_Unit.py](KLine/KLine_Unit.py) | 🔴 complex | **最小数据单元**：OHLCV + 时间 + 指标，多级别父子关系 |
| [KLine/KLine.py](KLine/KLine.py) | 🟡 moderate | 合并 K 线：包含处理后的合并结果，分形有效性校验 |
| [KLine/KLine_List.py](KLine/KLine_List.py) | 🔴 complex | **计算调度中枢**：fan-out 最高（26），协调笔/段/中枢/买卖点的完整计算流程 |
| [KLine/TradeInfo.py](KLine/TradeInfo.py) | 🟢 simple | 交易信息容器：存储技术指标数据 |

#### Bi — 笔的构建

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Bi/Bi.py](Bi/Bi.py) | 🔴 complex | **笔实体**：方向、起止端点、MACD 指标、虚实笔切换 |
| [Bi/BiList.py](Bi/BiList.py) | 🔴 complex | **笔列表管理器**：分形检测、构建笔、确认笔、虚拟笔管理 |
| [Bi/BiConfig.py](Bi/BiConfig.py) | 🟢 simple | 笔计算配置参数 |

#### Seg — 线段划分

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Seg/SegListComm.py](Seg/SegListComm.py) | 🔴 complex | **段算法公共基类**：段收集、左段处理、虚段处理 |
| [Seg/SegListChan.py](Seg/SegListChan.py) | 🟡 moderate | **默认段算法**（缠论原文）：特征序列分形法 |
| [Seg/SegListDYH.py](Seg/SegListDYH.py) | 🟡 moderate | 都业华版段算法（已弃用） |
| [Seg/SegListDef.py](Seg/SegListDef.py) | 🟡 moderate | 定义版段算法（已弃用） |
| [Seg/Eigen.py](Seg/Eigen.py) | 🟢 simple | 特征序列元素：继承 KLine_Combiner |
| [Seg/EigenFX.py](Seg/EigenFX.py) | 🔴 complex | **特征序列分形**：第一/二/三元素处理、有效突破判断 |
| [Seg/Seg.py](Seg/Seg.py) | 🔴 complex | **段实体**：起止笔、中枢列表、斜率/振幅/MACD |
| [Seg/SegConfig.py](Seg/SegConfig.py) | 🟢 simple | 段算法配置 |

#### ZS — 中枢构建

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [ZS/ZS.py](ZS/ZS.py) | 🔴 complex | **中枢实体**：区间范围、子中枢合并、背驰判断 |
| [ZS/ZSList.py](ZS/ZSList.py) | 🔴 complex | **中枢列表管理器**：中枢构建、增量更新、基于段的中枢归类 |
| [ZS/ZSConfig.py](ZS/ZSConfig.py) | 🟢 simple | 中枢配置 |

#### BuySellPoint — 买卖点

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [BuySellPoint/BSPointList.py](BuySellPoint/BSPointList.py) | 🔴 complex | **买卖点检测**：T1/T1P/T2/T2S/T3A/T3B 六类买卖点 |
| [BuySellPoint/BS_Point.py](BuySellPoint/BS_Point.py) | 🟡 moderate | 单个买卖点实体：类型、关联笔、属性叠加 |
| [BuySellPoint/BSPointConfig.py](BuySellPoint/BSPointConfig.py) | 🟡 moderate | 买卖点配置：按类型差异化参数覆盖 |

#### ChanModel — ML 特征

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [ChanModel/Features.py](ChanModel/Features.py) | 🟢 simple | ML 特征容器：字典式特征存取接口 |

### 5. 入口/门面层（5 文件）

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Chan.py](Chan.py) | 🔴 complex | **主入口类 CChan**：门面模式，批量/步进双模式，序列化 |
| [ChanConfig.py](ChanConfig.py) | 🟡 moderate | 配置系统：组装子配置，ConfigWithCheck 严格校验 |
| [main.py](main.py) | 🟢 simple | 演示入口：加载 sz.000001 日线并绘图 |
| [App/ashare_bsp_scanner_gui.py](App/ashare_bsp_scanner_gui.py) | 🔴 complex | A 股买卖点扫描器 GUI（PyQt6） |

### 6. 可视化层（4 文件）

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Plot/PlotDriver.py](Plot/PlotDriver.py) | 🔴 complex | **matplotlib 绘图核心驱动**：K线/笔/段/中枢/买卖点/指标渲染 |
| [Plot/AnimatePlotDriver.py](Plot/AnimatePlotDriver.py) | 🟢 simple | 步进回放动画驱动（Jupyter Notebook 内嵌） |
| [Plot/PlotMeta.py](Plot/PlotMeta.py) | 🟡 moderate | 绘图元数据：缠论元素 → matplotlib 结构化数据转换 |

### 7. 演示与测试层（6 文件）

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [Debug/strategy_demo.py](Debug/strategy_demo.py) | 🟢 simple | 步进回放策略演示 |
| [Debug/strategy_demo2.py](Debug/strategy_demo2.py) | 🟢 simple | 外部推送回测演示 |
| [Debug/strategy_demo3.py](Debug/strategy_demo3.py) | 🟡 moderate | 小级别触发大级别重算（区间套） |
| [Debug/strategy_demo4.py](Debug/strategy_demo4.py) | 🟢 simple | 多级别无时间对齐推送 |
| [Debug/strategy_demo5.py](Debug/strategy_demo5.py) | 🟡 moderate | ML 特征生成 + XGBoost 训练 |
| [Debug/strategy_demo6.py](Debug/strategy_demo6.py) | 🟡 moderate | 模型预测演示 |

### 8. 文档与配置层（9 文件）

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| [README.md](README.md) | 🔴 complex | **完整使用文档**（~1500 行）：功能介绍、API 详解、自定义开发 |
| [quick_guide.md](quick_guide.md) | 🟡 moderate | 快速上手指南（~570 行）：常见问题排查、核心能力 |
| [代码走读说明.md](代码走读说明.md) | 🔴 complex | **代码阅读路线图**（~800 行）：十个阶段循序渐进 |
| [阅读文档.md](阅读文档.md) | 🔴 complex | 面向初学者的指南（~1500 行）：六大部分模块级别拆解 |
| [CLAUDE.md](CLAUDE.md) | 🟡 moderate | AI 辅助开发参考文档 |
| [Script/requirements.txt](Script/requirements.txt) | 🟢 simple | Python 依赖清单 |

---

## 关键概念

### 计算流水线

缠论的核心计算遵循严格的递推顺序，每一层依赖前一层的输出：

```
原始K线 → CKLine_Unit
  ↓ 包含处理（Combiner）
合并K线 → CKLine
  ↓ 分形检测
分形 → 顶分型/底分型
  ↓ 相邻顶底分形连接
笔 → CBi
  ↓ 特征序列分形
线段 → CSeg
  ↓ 三段重叠
中枢 → CZS
  ↓ 背驰判断
买卖点 → CBS_Point（T1/T1P/T2/T2S/T3A/T3B）
```

### 两种运行模式

| 模式 | `trigger_step` | 行为 | 用途 |
|------|---------------|------|------|
| 批量模式 | `False` | 加载全部数据后一次性计算 | 一次性分析、静态绘图 |
| 步进模式 | `True` | 每根新 K 线产出快照（生成器） | 回测、动画播放 |

### 缓存机制

`@make_cache` 装饰器将计算结果绑定到实例的 `_memoize_cache` 字典上，与 `functools.lru_cache` 不同：
- 每个实例有独立的缓存空间
- 通过 `clean_cache()` 主动失效
- 当底层 K 线数据变更时，所有派生属性重新求值

### 配置校验

`ConfigWithCheck` 包装器使用"消费 key"模式：
- 子配置类从字典中取出自己关心的 key
- 包装器检查字典是否为空
- 若有剩余 key → 抛出异常（拼写错误立即发现）

### 序列化陷阱

`CChan.__deepcopy__` 手动重建跨级别的 `sup_kl`/`sub_kl_list` 指针图。pickle 序列化前临时移除 `pre`/`next` 链表指针，并调整 `sys.setrecursionlimit` 以避免递归溢出。

---

## 学习路径（12 步）

### 第 1 步：项目概览 — 缠论技术分析框架

从 [README.md](README.md) 开始，了解整个项目的全貌。这份约 1500 行的中文文档覆盖了缠论框架的核心功能（基本元素计算、策略买卖点、ML 对接、线上交易）、目录结构、CChan/CChanConfig 使用详解、画图配置、中枢算法、策略回测、自定义开发（数据接入、笔/线段/买卖点/模型扩展）等全部内容，是后续深入代码之前必读的导航地图。

### 第 2 步：应用入口 — main.py 与批量计算流程

[main.py](main.py) 是项目的标准演示入口，它加载 sz.000001（平安银行）的日线 K 线数据，实例化 CChan 门面类执行完整的缠论计算流水线，并调用绘图模块输出静态图表或动画回放。阅读这个文件可以快速理解从「数据加载 → 配置组装 → 缠论计算 → 结果可视化」的完整调用链路。

### 第 3 步：配置系统 — CChanConfig 与严格校验机制

[ChanConfig.py](ChanConfig.py) 是项目的配置中枢，CChanConfig 组装笔（BiConfig）、段（SegConfig）、中枢（ZSConfig）、买卖点（BSPointConfig）四类子配置。ConfigWithCheck 包装器通过消费 key 并检测未使用 key 来抛出异常，实现了严格的配置校验——任何拼写错误的配置项都会被立即发现。

> **Python 知识点**：ConfigWithCheck 使用"消费 key"模式实现配置校验。这是一种比 pydantic 更轻量的方案，适合不需要数据模型的场景。

### 第 4 步：基础公共层 — 枚举体系、异常处理与工具函数

[Common/](Common/) 目录是整个项目的底层依赖，fan-in 最高（CEnum.py 被 41 处引用）。CEnum.py 定义了 15 个核心枚举类，是整个代码库的"类型词汇表"。ChanException.py 提供 30+ 错误码的异常体系，func_util.py 包含 `has_overlap`（区间重叠判断）等关键工具函数。

> **Python 知识点**：Python 枚举（IntEnum）在缠论中被大量使用，因为它天然支持整数值比较和成员名称的可读性。例如 `KL_TYPE.K_DAY > KL_TYPE.K_60M` 可以直接比较级别大小。

### 第 5 步：缓存机制 — @make_cache 装饰器与实例级记忆化

[Common/cache.py](Common/cache.py) 实现了 `@make_cache` 装饰器，将计算结果绑定到实例的 `_memoize_cache` 字典上。当底层 K 线数据变更时，调用 `clean_cache()` 使缓存失效。CBi 和 CKLine_Combiner 大量使用这一机制来缓存昂贵的计算。

> **Python 知识点**：与 `functools.lru_cache` 不同，`@make_cache` 将缓存绑定到实例而非函数，每个实例有独立的缓存空间，且可通过 `clean_cache()` 主动失效。在状态频繁变更的增量计算场景中，这种设计避免了全局缓存的污染问题。

### 第 6 步：主门面类 — CChan 的多级别递归与模式切换

[Chan.py](Chan.py) 的 CChan 类是项目的核心门面，封装了多级别 K 线加载、递归计算流水线、序列化与反序列化。它支持两种运行模式：批量模式（一次性计算）和步进模式（生成器，每根新 K 线产出快照）。`__deepcopy__` 手动重建跨级别 K 线指针图，pickle 序列化前临时移除 pre/next 链表指针以避免递归溢出。

> **Python 知识点**：CChan 的步进模式使用了 Python 的 `yield` 机制——每次 yield 返回当前状态的快照，调用方可以像遍历列表一样逐根 K 线消费计算进度。这种"惰性计算"模式避免了在回测中一次性加载全部历史快照的内存开销。

### 第 7 步：数据适配层 — 多数据源统一接口

[DataAPI/](DataAPI/) 目录通过抽象基类 CommonStockAPI 定义了统一的 K 线数据获取接口，BaoStockAPI、AkshareAPI、csvAPI、ccxt 等子类分别适配不同的数据源。通过传入 `'custom:ModuleName.ClassName'` 字符串，还可以接入自定义数据源。

> **Python 知识点**：抽象基类（ABC）定义了 `get_kl_data()` 等统一接口，各数据源子类只需实现这些方法即可无缝接入缠论框架。这种"适配器模式"让计算核心与数据来源完全解耦。

### 第 8 步：K 线数据管线 — CKLine_Unit、CKLine 与 KLine_List

[KLine/](KLine/) 目录是缠论计算的数据基础层。CKLine_Unit 是最小数据单元，封装单根 K 线的 OHLC 数据；CKLine 在每个 CKLine_Unit 上计算技术指标；KLine_List 是 K 线列表管理器，负责调度逐根 K 线的计算流程，并维护子级别 K 线列表的父子关系（通过 `set_klu_parent_relation` 建立区间套所需的跨级别关联）。

> **Python 知识点**：KLine_List 的 fan-out 达到 26（项目第二高），说明它是整个计算流水线的调度中枢。它体现了"管道-过滤器"架构模式——每个模块只负责一个转换步骤，KLine_List 作为管道将它们串联起来。

### 第 9 步：包含处理与笔的构建 — Combiner 与 Bi 模块

[Combiner/KLine_Combiner.py](Combiner/KLine_Combiner.py) 处理 K 线包含关系（当一根 K 线完全包含前一根时，按趋势方向合并），这是缠论特有的预处理步骤。[Bi/](Bi/) 模块在此基础上检测分形，并将相邻的顶底分形连接成笔（Bi）。

> **Python 知识点**：K 线包含处理是缠论区别于其他技术分析的核心步骤之一。当一根 K 线的高低点完全包含前一根 K 线时，需要根据趋势方向决定保留哪根 K 线——上升趋势保留高点更高的，下降趋势保留低点更低的。这一预处理保证了后续分形检测的准确性。

### 第 10 步：线段划分 — 特征序列分形与三段算法

[Seg/](Seg/) 模块将笔连接成线段（Seg），这是缠论中最复杂的计算环节。CSegListComm 是所有段算法的基类，包含未确认段（虚段）的复杂处理逻辑。SegListChan.py 是默认算法，使用特征序列分形来判定段的结束。SegListDYH.py（都业华版）和 SegListDef.py（定义版）提供替代算法。

> **Python 知识点**：特征序列（EigenSequence）是缠论线段划分的核心概念——将一段笔中的每一笔视为一个特征序列元素，当特征序列出现分形时，才确认前一段的结束。"虚段"处理反映了线段划分的实时性——在步进模式下，当前线段可能尚未确认，需要支持"未确认段"的临时状态。

### 第 11 步：中枢与买卖点 — 缠论策略的核心输出

[ZS/ZSList.py](ZS/ZSList.py) 在线段的基础上构建中枢——三段重叠的区间，并根据中枢的延伸、扩展、新生关系进行合并。[BuySellPoint/BSPointList.py](BuySellPoint/BSPointList.py) 检测六类买卖点（T1/T1P/T2/T2S/T3A/T3B），基于中枢背驰、MACD 背离等条件判断。这是缠论策略的最终输出层。

> **Python 知识点**：中枢合并是缠论中一个精妙的递推问题——当新的线段延伸后，已有的中枢可能被扩展或合并，需要重算区间。ZSList 采用增量更新策略——每次新线段到达时，仅检查受影响的中枢，而非全量重算，这对步进模式的性能至关重要。

### 第 12 步：技术指标、可视化与实战演练

[Math/](Math/) 目录包含手写实现的 MACD、BOLL、RSI、KDJ、DeMark 序列等技术指标（不依赖 talib）。[Plot/PlotDriver.py](Plot/PlotDriver.py) 使用 matplotlib 将 K 线、笔、段、中枢、买卖点完整渲染成图表。最后，[Debug/strategy_demo.py](Debug/strategy_demo.py) 展示了步进回放模式的实际用法，而 [代码走读说明.md](代码走读说明.md) 提供了按十个阶段循序渐进的代码阅读路线图。

> **Python 知识点**：手写技术指标而不依赖 talib 的设计决策，使得缠论框架完全自包含——无需安装 C 扩展库即可在任意 Python 3.11+ 环境中运行。MACD 的 DEA/DIF 双重平滑计算、BOLL 的标准差带宽计算，均用纯 NumPy 实现，保证了跨平台兼容性。

---

## 复杂度热点

以下文件复杂度最高，建议在熟悉基础架构后再深入阅读：

| 文件 | 说明 |
|------|------|
| [Chan.py](Chan.py) | 主入口类：多级别递归、序列化陷阱、双模式切换 |
| [Combiner/KLine_Combiner.py](Combiner/KLine_Combiner.py) | K 线包含处理基类：项目中最关键的基类之一 |
| [Bi/Bi.py](Bi/Bi.py) | 笔实体：方向、端点、MACD 指标、虚实笔切换 |
| [Bi/BiList.py](Bi/BiList.py) | 笔列表管理器：分形检测、笔构建、虚拟笔管理 |
| [Seg/SegListComm.py](Seg/SegListComm.py) | 段算法基类：段收集、虚段处理 |
| [Seg/EigenFX.py](Seg/EigenFX.py) | 特征序列分形：段结束判断的核心逻辑 |
| [Seg/Seg.py](Seg/Seg.py) | 段实体：起止笔、中枢列表、MACD 指标 |
| [ZS/ZS.py](ZS/ZS.py) | 中枢实体：区间范围、子中枢合并、背驰判断 |
| [ZS/ZSList.py](ZS/ZSList.py) | 中枢列表管理器：构建、增量更新、合并 |
| [BuySellPoint/BSPointList.py](BuySellPoint/BSPointList.py) | 买卖点检测：六类买卖点、盘整背驰 |
| [KLine/KLine_List.py](KLine/KLine_List.py) | 计算调度中枢：fan-out 最高（26） |
| [KLine/KLine_Unit.py](KLine/KLine_Unit.py) | K 线核心数据结构：OHLCV + 指标 + 父子关系 |
| [Math/Demark.py](Math/Demark.py) | DeMark 序列：Setup + Countdown 两阶段引擎 |
| [Plot/PlotDriver.py](Plot/PlotDriver.py) | matplotlib 绘图核心驱动 |
| [README.md](README.md) | 完整使用文档（~1500 行） |
| [代码走读说明.md](代码走读说明.md) | 代码阅读路线图（~800 行） |

---

## 目录结构速查

```
chan.py/
├── Chan.py                 ← 主入口类 CChan
├── ChanConfig.py           ← 配置系统
├── main.py                 ← 演示入口
├── Common/                 ← 基础公共层（枚举、异常、缓存、工具）
├── Math/                   ← 技术指标层（MACD/BOLL/RSI/KDJ/DeMark/趋势线）
├── DataAPI/                ← 数据适配层（BaoStock/Akshare/CCXT/CSV）
├── Combiner/               ← K 线包含处理
├── KLine/                  ← K 线数据结构与调度
├── Bi/                     ← 笔的构建与管理
├── Seg/                    ← 线段划分（3 种算法）
├── ZS/                     ← 中枢构建与合并
├── BuySellPoint/           ← 买卖点检测
├── ChanModel/              ← ML 特征容器
├── Plot/                   ← matplotlib 可视化
├── Debug/                  ← 策略演示脚本
├── App/                    ← GUI 扫描器
└── Script/                 ← 依赖清单
```

---

## 快速开始

```bash
# 安装依赖
pip install -r Script/requirements.txt

# 运行主演示（计算 sz.000001 日线缠论并绘图）
python main.py

# 运行策略回测演示
python Debug/strategy_demo.py     # step-playback 回测
python Debug/strategy_demo2.py    # 外部推送回测
python Debug/strategy_demo3.py    # 小级别触发大级别重算
python Debug/strategy_demo4.py    # 多级别无时间对齐推送
python Debug/strategy_demo5.py    # ML 特征生成 + XGBoost 训练
python Debug/strategy_demo6.py    # 模型预测
```

---

> 🤖 本指南由 [Understand-Anything](https://github.com/Understand-Anything/understand-anything-plugin) 基于知识图谱自动生成。
> 建议将此文件保存到 `docs/ONBOARDING.md` 并提交到仓库供团队使用。