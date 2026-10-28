# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

chan.py 是缠论（Chan Theory）技术分析的 Python 实现，用于从 K 线数据计算分形、笔、线段、中枢、买卖点。这是**开源版**（约 5300 行），完整版（约 22000 行）的策略、交易引擎、ML/AutoML 模块未包含在本仓库中。

- 作者: Vespa314, MIT 协议
- 要求 **Python >= 3.11**
- 文档: `README.md`（~1500 行中文，是主要参考文档）、`quick_guide.md`

## 常用命令

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

# GUI 扫描器（需要 akshare + PyQt6）
python App/ashare_bsp_scanner_gui.py
```

本项目**无自动化测试**，`Debug/strategy_demo*.py` 脚本充当手动冒烟测试。

## 核心架构

### 计算流水线

```
CChan (Chan.py)  ← 门面，接收 stock code + CChanConfig
  │
  ├─ DataAPI/  ← 数据源适配器（BaoStock/Akshare/CCXT/CSV/custom）
  │   └─ 自定义数据源: 传入 "custom:ModuleName.ClassName" 字符串
  │
  ├─ load_iterator()  ← 递归加载多级别 K 线，建立父子关系
  │   │
  │   ├─ CKLine_Combiner  ← K 线包含处理/合并
  │   ├─ CBiList          ← 分形检测 → 笔的构建
  │   ├─ (step mode)      ← trigger_step=True 时，每根 K 线都会重算段/中枢/买卖点
  │   │
  │   └─ cal_seg_and_zs() ← 最终化：段、中枢、买卖点
  │       ├─ CSegListChan  ← 默认段算法（特征序列分形）
  │       ├─ CZSList       ← 中枢构建与合并
  │       └─ CBSPointList  ← 买卖点（T1/T1P/T2/T2S/T3A/T3B）
  │
  └─ 结果访问: chan[KL_TYPE].bi_list / .seg_list / .zs_list / .bs_point_lst
```

### 多级别递归

`CChan.load_iterator` 从最高级别向最低级别递归，每个父 K 线通过 `set_klu_parent_relation` 连接到子 K 线，支持区间套策略（在父 K 线下查看子级别买卖点）。

### 两种运行模式

- **批量模式** (`trigger_step=False`): 加载全部数据后一次性计算所有元素
- **步进模式** (`trigger_step=True`): `CChan` 变为生成器，每根新 K 线产生一个快照，用于回测和动画播放

### 配置系统

`CChanConfig` 接受字典，组成子配置（`CBiConfig`, `CSegConfig`, `CZSConfig`, `CBSPointConfig`）。`ConfigWithCheck` 包装器会消费 key 并在遇到未知 key 时抛出异常——严格的配置校验。支持通过 `-buy`/`-sell`/`-seg` 后缀实现按买卖点类型的参数覆盖。

## 关键实现细节

### 缓存机制 (`Common/cache.py`)

`@make_cache` 装饰器将缓存绑定到实例的 `self._memoize_cache` 上。`CBi` 和 `CKLine_Combiner` 大量使用它来缓存昂贵的派生属性。当底层状态变更时调用 `clean_cache()` 使缓存失效。

### 序列化陷阱 (`Chan.py`)

`CChan.__deepcopy__` 手动重建跨级别的 `sup_kl`/`sub_kl_list` 指针图。`chan_dump_pickle`/`chan_load_pickle` 在 pickle 前临时移除 `pre`/`next` 链表指针（并调整 `sys.setrecursionlimit`），以避免 pickle 递归溢出，之后恢复。

### 段算法

三种段算法，均继承 `CSegListComm`：
- `chan`（默认，`SegListChan.py`）：特征序列分形
- `1+1`（`SegListDYH.py`，已弃用）：都业华版
- `break`（`SegListDef.py`，已弃用）：定义版

`CSegListComm` 包含未确认段（虚段）的复杂处理逻辑。

### 绘图

- `CPlotDriver`：matplotlib 静态渲染，输出 PNG
- `CAnimateDriver`：步进回放动画，支持 Jupyter Notebook 内嵌

### 指标

所有技术指标均为手写实现（MACD, BOLL, RSI, KDJ, DeMark, TrendLine），不依赖 talib。

## 目录结构速查

| 目录 | 用途 |
|------|------|
| `Chan.py` | 主入口类 `CChan` |
| `ChanConfig.py` | 配置系统 `CChanConfig` |
| `Common/` | 枚举、异常、缓存、工具函数 |
| `KLine/` | K 线单元、合并 K 线、K 线列表容器 |
| `Combiner/` | K 线包含处理/合并逻辑 |
| `Bi/` | 笔的构建与管理 |
| `Seg/` | 段算法（特征序列、虚段处理） |
| `ZS/` | 中枢构建与合并 |
| `BuySellPoint/` | 买卖点计算 |
| `Math/` | 手写技术指标 |
| `DataAPI/` | 数据源适配器（BaoStock 默认） |
| `Plot/` | matplotlib 绘图 |
| `Debug/` | 策略演示/手动测试脚本 |
| `ChanModel/` | ML 特征容器（开源版中不完整） |