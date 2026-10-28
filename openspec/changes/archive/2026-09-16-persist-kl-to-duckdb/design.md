## Context

数据流的现状（见 proposal.md - Why）：DataAPI 适配器是只读生成器，`CCommonStockApi.get_kl_data()` 逐根产出 `CKLine_Unit`，`CChan.load_iterator()` 消费后把结果放进内存 `CChan.kl_datas`。适配器契约只有四个方法：`__init__(code, k_type, begin_date, end_date, autype)`、`get_kl_data()`、`SetBasciInfo()`、`do_init()`/`do_close()`（类方法）。

两个既有机制让本次改造无需触碰核心：

1. **自定义数据源**：`CChan._get_stockapi_cls` 支持 `data_src = "custom:package.Class"`，经 `importlib.import_module(f"DataAPI.{package}")` 动态加载适配器。新增一个 DuckDB 适配器只需落到 `DataAPI/` 下，零侵入。
2. **字段映射**：`DATA_FIELD` 枚举定义了 `time_key/open/high/low/close/volume/turnover/turnover_rate`，`CKLine_Unit` 构造即消费这套字段，schema 可与之一一对应。

## Goals / Non-Goals

**Goals:**
- 把原始 K 线（OHLCV + 时间 + `code`/`kl_type`/`autype` 元信息）持久化到本地 DuckDB 单文件。
- 让计算阶段完全离线：`CChan` 从 DuckDB 读数据，与网络解耦。
- 灌数可重复、可中断、幂等：重复跑不产生脏数据，中断后重启自动从断点续拉。

**Non-Goals:**
- 不持久化笔/段/中枢/买卖点等计算产物（它们由 `CChan` 每次现算，属纯函数推导）。
- K 线分析数据本身不引入服务端数据库（仍用 DuckDB 单文件，无服务/事务/多用户）；PG 作为规划中的业务 web 系统库存在，本变更仅借用其存操作态（重算游标、灌数任务状态），不把 K 线搬进 PG。
- 不改动任何缠论计算算法与配置系统。
- 不做复权因子表（存不复权价 + 因子现算复权价），本期直接存 QFQ/HFQ 结果。
- 不做 tick 级实时行情订阅（盘中为分钟级轮询已收盘 bar，仍属定时批处理范畴）。

## Decisions

### D1. 存储引擎：DuckDB 原生单文件（而非 PG、而非裸 Parquet）

数据形态是 append-only 的列式时序数据，用途是单用户离线分析（OLAP），无事务/并发/远程访问诉求。

- 弃 **PostgreSQL**：需要服务端进程、连接管理、部署运维；对"单机、单文件、只读分析"这一场景是过度设计，改造工作量显著更大（schema 迁移、连接池、序列化），而分析效率对列式扫描反而无优势。
- 弃 **裸 Parquet 分文件**：去重、区间过滤、追加都需手写 Python 逻辑（追加 = 读旧文件 + 合并 + 覆盖）；且无法跨股票单文件聚合。Parquet 保留为后续可选归档导出，不作为主存储。
- 选 **DuckDB 原生文件**：`pip install duckdb` 单依赖；SQL 原生支持区间过滤、`INSERT OR REPLACE` 去重、`ALTER TABLE ADD COLUMN` 演进；可 `COPY ... TO '*.parquet'` 导出归档。

### D2. 表结构：复合主键 `(code, kl_type, autype, time_key)`

一行 = **一根 K 线**，而非一只股票。`code` 单独不唯一（同一股票有成千上万根历史 K 线），真正唯一标识一根 K 线的是四个维度：

| 维度 | 语义 |
|------|------|
| `code` | 哪只股票（`sz.000001`） |
| `kl_type` | 哪个级别（`K_DAY`/`K_60M`，存 `KL_TYPE.name`） |
| `autype` | 哪种复权（`QFQ`/`HFQ`/`NONE`，存 `AUTYPE.name`） |
| `time_key` | 哪个时间点（规范化北京时间字符串 `"YYYY-MM-DD HH:MM:SS"`，见下） |

`time_key` 用 `VARCHAR` 存规范化字符串，而非 `TIMESTAMP`：日线的 hour/minute/second 均为 0，`CTime.to_str()` 会省略时间部分，用 `TIMESTAMP` 会引入时区与"零时刻"语义歧义；字符串能无损往返 `CTime` 的全部字段，且区间过滤按字典序即按时间序（固定宽度、补零）。`_normalize_time` 负责把纯日期边界补为 `00:00:00`/`23:59:59`。

弃代理键 `id BIGSERIAL`：本库是单表分析库，没有第二张表外键引用"某根 K 线"，代理键无 join 对象，反而多一层间接。复合自然键恰好就是读适配器的查询条件，且 `time_key` 参与主键让 DuckDB 的 zonemap（min/max）剪枝能加速区间扫描。

```sql
CREATE TABLE kline (
  code      VARCHAR,
  kl_type   VARCHAR,
  autype    VARCHAR,
  time_key  VARCHAR,   -- "YYYY-MM-DD HH:MM:SS" 规范化北京时间字符串
  open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
  volume DOUBLE, turnover DOUBLE, turnover_rate DOUBLE,
  PRIMARY KEY (code, kl_type, autype, time_key)
);
```

### D3. 接入方式：独立读适配器 + 独立写脚本（而非写穿缓存）

写穿缓存（在 `CChan` 里加"取数时顺便写库"）会把持久化耦合进计算流水线，改 `CChan`、加配置项、污染热路径。独立方案下：

- **写路径** `Debug/download_kl.py`：复用现有 BaoStock/Akshare 适配器拉数 → 转 DataFrame → `KLineStore.upsert`。
- **读路径** `DataAPI/DuckDBAPI.py`：`CDuckDB` 继承 `CCommonStockApi`，`get_kl_data()` 查 DuckDB 后 yield `CKLine_Unit`。

读路径靠既有 `custom:` 机制接入，`CChan` 零改动；读写职责分离，各自可独立测试。

### D4. 断点续拉：断点 = 表内 `max(time_key)`，配合幂等 upsert

不做独立游标文件（游标会与真实数据脱节，如"拉完但未写游标就崩"）。起始日期每次现查：

```
start = SELECT max(time_key)
        FROM kline
        WHERE code=? AND kl_type=? AND autype=?
-- NULL（从未下过）→ start = 配置的最早日期（全量）
-- 有值           → start = 该值（回看 N 天自愈，如 3 天）
```

写入用 `INSERT OR REPLACE`（按复合主键去重）：重复下载同一区间是无害覆盖，中断后漏写的尾部下次自动补齐。因此"重新接入 vs 断点接入"不再二选一——默认就是断点增量，`--full` 作为手动兜底（数据坏了、复权修订时）。

示例：9/1 首跑全量至 `max(time_key)=2026-09-01`；9/6 再跑，start 取 09-01（回看几天），仅增量补 09-02~09-06。中断在 09-04，重启后 start 仍是 09-04，重拉 [09-01, 09-06] 覆盖旧行 + 补齐 09-05/09-06。

### D5. 复权处理：直接存 QFQ/HFQ 结果 + `--full` 定期重刷

前/后复权历史价格在分红送股/除权除息时会**整体重算**，因此 QFQ/HFQ 数据并非严格 append-only。本期采用简单方案：直接存复权结果，日常增量追加；除权事件后或定期用 `--full` 全量重刷。存"不复权价 + 复权因子表、用时现算"的规范方案留待数据量/正确性要求升级后再议（见 Open Questions）。

### D6. 灌数形态：定时批处理（而非常驻守护进程）

K 线只在收盘时"长出新根"，无需常驻连接等待。落地为 cron/定时调度，每次运行短促、幂等，可随时手动补跑；这也大幅缩小"中断"问题的分量。日线/盘后灌数走此路径；盘中分钟级接入见 D7。

### D7. 盘中实时接入：短周期轮询 + 只收已收盘 bar + 水位通知 + 全量重算优先

盘中按 5min/30min 级别计算买卖点时，灌数从"盘后批量"变为"盘中短周期轮询"，并需在数据落库后自动触发重算。四条子决策：

- **轮询间隔 = 最细 bar 周期的 1/5~1/3，默认统一 1 分钟**：覆盖 5min/30min/日线；只在交易时段（A 股 09:30–11:30、13:00–15:00）运行，收盘后补拉一次收尾。非交易时段空转无害（幂等 upsert 无写入）。
- **只持久化并计算已收盘的 bar**：形成中（forming）的 bar 其 high/low/close 仍在变，喂给分型/笔会反复翻转，故以 `time_key` 的 bar 收盘时刻 ≤ now 作为"已收盘"判据；形成中的最新 bar 仅作展示，不进计算。
- **通知 = DuckDB 表内水位 `max(time_key)`**：灌数写库后水位前进；重算进程维护 `last_processed_time` 游标（存 PG 业务库，见 D14），轮询到新 bar 即取增量重算。水位由数据派生（DuckDB 的 `max(time_key)`），游标是操作态（存 PG，与分析库解耦，避免 DuckDB 单写者冲突），at-least-once 可恢复。不上 Redis/MQ（单机单用户无需消息中间件）。
- **重算先全量后增量**：先复用批模式 `CChan` 每次从 DuckDB 读全历史 `[begin, now]` 重算（几只股票、分钟级历史量小，成本毫秒~低秒级）；`CChan` 已有 `trigger_load`/`step_load` 增量钩子，留作历史极长/股票众多时的优化。

**数据源现实**：BaoStock 分钟数据偏历史、有延迟，盘中准实时分钟线走 Akshare 的东财/新浪接口，需独立的分钟级数据源适配器（不复用日线拉取路径）。

### D8. 数据校验与质量

买卖点对价格异常极敏感，一根脏 K 线会直接造出假分型/假买卖点。入库前做结构性校验，区分"结构性非法"（拒绝）与"疑似异常"（告警但保留）：

| 校验 | 规则 | 不通过处理 |
|------|------|------|
| OHLC 合法性 | `high ≥ max(open,close)`、`low ≤ min(open,close)`、`high ≥ low`、价格非负 | 拒绝写入 + 告警 |
| 时间单调性 | 同一 `(code,kl_type,autype)` 的 `time_key` 严格递增 | 拒绝乱序；重复按幂等去重 |
| 异常跳变 | 单根涨跌幅超阈值（如 ±20%，可配） | 告警但保留 |

关键边界：**不复权（NONE）数据在除权除息日会真实跳空**，这不是脏数据。校验层只判"结构是否非法"，不越界判"价格对不对"；跳变阈值仅作告警提示人工复核，不拒绝写入。

### D9. 完整性：缺口检测 + 区间重刷

D4 的断点只能补**尾部**，补不了**中间洞**——某天网络失败漏了中间一根 bar，`max(time_key)` 已走到更晚，洞永远不会被发现。补两个正交能力：

- **缺口检测**：入库后按交易日历检查 `time_key` 连续性，发现缺交易日则记录缺口，触发针对该区间的补拉。与 D4 断点互补：断点管"从哪接着拉"，缺口管"已拉的历史有没有洞"。
- **区间重刷**：CLI 支持 `--begin/--end`，只 `DELETE` 指定区间后重拉再 upsert。作为 `--full`（全量）与日常增量之间的中间态，用于数据源修订某段历史（复权调整、停牌复牌补数据）时不至于全量重刷。

### D10. 交易日历 + 时区

盘中"已收盘"判断、缺口检测、调度都依赖"哪天是交易日"，且各数据源时间格式/时区不一：

- **时区**：`time_key` 统一存**无时区的北京时间**（A 股 K 线数据源普遍返回本地时间字符串，无 tz），写入前在适配层规范化；如后续跨市场再评估 UTC。
- **交易日历**：复用 `exchange_calendars` 类库，锚定"已收盘""连续交易日""缺口""盘中调度是否运行"。节假日休市时调度空转无害，但缺口检测与已收盘判断必须锚定日历而非简单的周一~周五。

### D11. 配置管理 + 可观测性

- **配置**：股票列表、级别、复权、轮询间隔、交易时段、库路径等集中到配置文件（YAML/JSON）；CLI 仅作单次覆盖。避免多股票批量灌数时 CLI 参数失控。
- **可观测**：
  - 结构化日志：每次灌数记录拉取量、写入量、各 `(code,kl_type)` 水位；
  - 状态可查：每股票最新 bar 时间、上次成功时间；
  - 告警：连续失败 N 次、水位长时间不前进（疑似数据源失效）。

### D12. 限频 / 退避 / 失败隔离

盘中轮询多只股票，东财/新浪等源有频率上限，且单只失败不应拖垮整体：

- **节流**：控制请求 QPS，轮询间隔留足余量；
- **指数退避**：失败后逐步拉长重试间隔并封顶，避免打爆被限频的源；
- **失败隔离**：以单只股票为粒度 `try/except`，一只失败不影响其余。

### D13. 首次回填断点续传

单股票全历史首次入库量大、耗时长、可能被限频打断。分批拉取 + 进度同样由数据派生（表内 `max(time_key)`），重跑不重拉、中断可续传。与 D4 同机制，只是针对"大批量回填"场景明确：按批次推进、进度可恢复，而非一次性拉全历史。

### D14. 存储拓扑：DuckDB 分析库 + PG 业务库分工

引入 PG 是出于"后续业务 web 系统"这一独立目标，而非替代 DuckDB 存 K 线。两库按数据性质分工：

| 库 | 承载 | 性质 |
|----|------|------|
| DuckDB（单文件） | 原始 K 线（分析数据） | 列式、离线重算、无服务、单写者 |
| PostgreSQL | 重算游标、灌数任务状态、（后续）web 业务数据 | 操作态/业务数据，多用户、事务 |

- **重算游标归 PG**：`last_processed_time` 是操作态而非分析数据，且 PG 本就为 web 系统引入；放 PG 同时化解 DuckDB 单写者冲突（重算进程若把游标写回 `kline` 库会与灌数抢写锁）。
- **K 线不进 PG**：D1 选型理由不变——K 线是 append-only 列式时序，DuckDB 才是主场；PG 只承载"状态与业务"，不承载"行情"。
- **边界准绳**：分析数据（K 线及其衍生计算）→ DuckDB；操作状态与业务数据 → PG。

## Risks / Trade-offs

- **[QFQ/HFQ 历史价过期]** 除权后未及时 `--full`，历史复权价失真 → 定时全量重刷 + 文档标注"复权价需定期刷新"。
- **[DuckDB 单写者]** DuckDB 文件同一时刻只允许一个写进程 → 灌数脚本串行化/定时调度，避免并发写同一库；读侧可多进程只读。
- **[schema 演进]** 将来加字段（如成交额、涨跌幅）→ DuckDB 原生 `ALTER TABLE ADD COLUMN`；主键不变，无需迁移工具。
- **[存储增长]** 多股票×多级别×多复权全历史会持续膨胀 → 长期可用 `COPY ... TO '*.parquet'` 按需归档冷数据；本期不处理。
- **[`kl_type`/`autype` 以 `.name` 字符串存储]** 读适配器需把字符串还原为 `KL_TYPE`/`AUTYPE` 枚举 → 在 `CDuckDB` 内做 name→enum 映射，集中在一处，避免散落。
- **[分钟级数据源可用性/延迟]** BaoStock 分钟数据偏历史，盘中依赖 Akshare/东财/新浪，各源延迟与限频不同 → 分钟级数据源与日线分离，独立适配器 + 独立限频策略，轮询间隔留足余量。
- **[forming bar 误入计算]** 未收盘 bar 若进入分型/笔会反复翻转 → 入库与计算严格按"收盘时刻 ≤ now"过滤，形成中 bar 仅展示不进计算。
- **[校验误杀真实跳空]** 除权除息导致的不复权跳空被阈值判为异常 → 跳变只告警不拒写，结构性非法才拒绝；阈值可配。
- **[交易日历维护成本]** 自维护日历需随交易所公告更新 → 优先复用现成库，日历数据独立可替换；缺口检测锚定日历而非简单按日连续。
- **[缺口检测开销]** 全量逐日扫连续性随历史增长变贵 → 增量检测（只查尾部）+ 定期全量扫描，缺口记录持久化避免重复扫。
- **[双库边界不清]** K 线进 DuckDB、操作态进 PG，边界若模糊会乱放 → 以"分析数据 vs 操作状态"为准绳：K 线/计算走 DuckDB，游标/任务/业务数据走 PG。

## Migration Plan

1. `pip install duckdb`，更新 `Script/requirements.txt`。
2. 新增 `DataAPI/KLineStore.py`（建表 + upsert + query），先独立冒烟：手动灌一小段数据，验证去重与区间查询。
3. 新增 `Debug/download_kl.py`，跑 `--code sz.000001 --kl-type K_DAY --autype QFQ`，灌入历史 K 线。
4. 新增 `DataAPI/DuckDBAPI.py`，在 `main.py` 将 `data_src` 切为 `"custom:DuckDBAPI.CDuckDB"` 对比 BaoStock 输出，确认笔/段结果一致。
5. 接入定时调度（cron），设置每日收盘后增量灌数。

回滚：本改造纯新增文件 + 一处依赖 + 可选的一行 `data_src` 切换；回滚即还原 `main.py` 的 `data_src` 为 `DATA_SRC.BAO_STOCK`，计算路径无任何残留依赖。

## Open Questions

- 是否后续演进为"存不复权价 + 复权因子表、复权价现算"，以彻底解决 QFQ/HFQ 历史重算问题？（不影响本期 schema/任务，可延后）
- 单库文件的规模上限与是否按 `code` 分区建多库，留待数据量实测后再定。（DuckDB 原生单文件对当前规模足够）
- `trigger_load`/`step_load` 对"live 实例追加单根 bar"的精确语义需实测确认；在重算成本可接受前先走 D7 的全量重算，增量步进留作优化。
- 计算结果（笔/段/中枢/买卖点）是否落库？Fork B 当前只持久化原始 K 线，但后续业务 web 系统若要展示买卖点，需决定"每次现算（+缓存）"还是"计算结果序列化落 PG 供直接读取"——这取决于 web 系统的展示内容与实时性要求，且会影响 proposal 的 capability 边界。待 web 需求明确后再定。
