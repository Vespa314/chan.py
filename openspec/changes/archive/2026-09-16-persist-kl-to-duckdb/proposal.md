## Why

当前 K 线数据每次运行都通过 DataAPI 适配器（BaoStock/Akshare）从网络实时拉取，数据不落盘、不可复现，重复分析要么反复请求网络（慢、受接口限频、依赖外部可用性），要么在内存里临时构建。把原始 K 线持久化到本地 DuckDB 后，后续缠论计算直接从本地库读取，网络请求只发生在"灌数"阶段，计算阶段完全离线。

## What Changes

- 新增 DuckDB 存储层 `DataAPI/KLineStore.py`：定义 `kline` 表结构、幂等写入（`INSERT OR REPLACE`）、按 `(code, kl_type, autype)` + 日期区间查询。
- 新增只读数据源适配器 `DataAPI/DuckDBAPI.py`：类 `CDuckDB` 继承 `CCommonStockApi`，从 DuckDB 读原始 K 线并逐根 yield `CKLine_Unit`，接入方式为 `data_src = "custom:DuckDBAPI.CDuckDB"`。
- 新增灌数脚本 `Debug/download_kl.py`：复用现有 BaoStock/Akshare 适配器拉取 → 转 DataFrame → 幂等写入 DuckDB；默认增量（从表内 `max(time_key)` 续拉），支持 `--full` 全量重刷。
- 新增分钟级盘中接入：短周期（默认 1 分钟）轮询拉取已收盘的 5min/30min bar 幂等入库，交易时段运行、收盘后补拉一次；分钟数据源独立于日线（BaoStock 分钟数据偏历史，盘中走 Akshare/东财/新浪）。
- 新增盘中重算通知：以 DuckDB 表内 `max(time_key)` 为水位，新 bar 落库后通知重算进程产出最新笔/段/中枢/买卖点；本期优先全量重算，`CChan` 步进模式（`trigger_load`/`step_load`）留作增量优化。
- 依赖新增 `duckdb`（`Script/requirements.txt`）。
- **不修改** `CChan`、`CBiList`、`CSegListChan` 等任何计算逻辑；计算流水线对数据来源无感知。

## Capabilities

### New Capabilities

- `kline-persistence`: 原始 K 线的本地持久化能力，覆盖存储 schema、幂等写入/去重、增量续拉与区间查询、数据校验与缺口检测/区间重刷、交易日历与配置/可观测，通过 `CCommonStockApi` 契约回读 K 线的数据源适配器，以及盘中的分钟级短周期接入与水位驱动的重算通知。

### Modified Capabilities

<!-- 无现有 capability 需要变更：本仓库尚无 openspec/specs/，且本次不改动任何既有计算行为。 -->

## Impact

- **新增文件**：`DataAPI/KLineStore.py`、`DataAPI/DuckDBAPI.py`、`Debug/download_kl.py`；盘中另需分钟级数据源适配器与盘中接入/重算引擎（具体文件待 tasks 阶段拆分）
- **修改文件**：`Script/requirements.txt`（新增 `duckdb`）
- **调用方式**：使用方将 `data_src` 从 `DATA_SRC.BAO_STOCK` 切换为 `"custom:DuckDBAPI.CDuckDB"`（示例见 `main.py`），计算逻辑无需改动
- **依赖**：新增第三方库 `duckdb`、`exchange_calendars`、PG 客户端驱动（`psycopg2`/`sqlalchemy`）；K 线分析数据仍为单文件 DuckDB（无服务），PG 仅承载操作态（重算游标、任务状态）与后续业务 web 系统数据；盘中分钟数据源依赖 Akshare/东财/新浪
