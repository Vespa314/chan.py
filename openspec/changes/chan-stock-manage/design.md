## Context

动机见 proposal.md - Why。这里只列决定方案所需的状态与约束：

- 买卖点模型：`CBS_Point`（`klu`/`is_buy`/`type`），类型 `BSP_TYPE`：T1/T1P/T2/T2S/T3A/T3B，方向由 `is_buy` 区分；`chan[KL_TYPE].bs_point_lst.getSortedBspList()` 可取排序后列表。
- 买卖点只现算不落库；缠论计算是递归结构，只能在完整历史（或「已确认前缀 + 续算」）上正确求值。
- chan.py 已具备续算基底：`trigger_load(inp)` 往已加载 `CChan` 追加新 K 线；`trigger_step=True` 下 `add_single_klu` 逐根触发 `cal_seg_and_zs()`，而 `cal_seg_and_zs` 用 `last_sure_seg_start_bi_idx`/`last_sure_segseg_start_bi_idx`/`last_sure_pos` 游标只重算未确认尾部；`chan_dump_pickle`/`chan_load_pickle`/`chan_pickle_restore` 全量序列化并恢复 `pre/next` 指针。
- 既有库分工（`persist-kl-to-duckdb`）：K 线分析数据落 DuckDB `kline`；操作态落 PG `recompute_cursor`（psycopg2 直写）。
- `IngestUtil.py` 提供 `get_calendar()`、`DEFAULT_STALE_HOURS`、灌数配置 schema；灌数配置骨架见 `ingest_config.example.json`。
- `chan-web-viewer`（进行中）规划 `WebAPI/`（FastAPI）+ `web/`（Vue3+Vite+TS），尚未落地，目录共享需协调。
- 无行业数据（`gen_stock_list.py` 只取 code+name）、无 LLM 集成、无调度器。

## Goals / Non-Goals

**Goals:**
- 用「增量续算引擎 + 买卖点索引」把缠论结论落库，让「全市场某日某买卖点查询 + 板块聚合」退化成 SQL。
- 提供 3 Tab（自选 / 历史买卖点 / 监控 + LLM 归因）的 Web 管理页，串起选股→跟踪→复盘闭环。
- 不改 `CChan` 计算逻辑，仅复用其 `trigger_step`/pickle 能力。

**Non-Goals:**
- 不实现 `chan-web-viewer` 的 K 线图渲染与「搜索标的」交互（本变更只提供其依赖的股票池/行业数据）。
- 不做灌数/下载本身的调度（`download_kl.py`/`intraday_poll.py` 职责），本变更只消费其结果触发续算。
- 不改 `kline`/`recompute_cursor` 既有 schema，不碰计算流水线。

## Decisions

### D1. 存储分工与 PG schema

原始 K 线继续 DuckDB；缠论结论 + 业务元数据落 PG（关系型、查询重、并发读写、行业 join 顺路）。PG 表清单：

```sql
stock            (code PK, name, exchange, enabled, kl_types VARCHAR[], autypes VARCHAR[],
                  tags VARCHAR[], notes TEXT, created_at, updated_at)          -- 去掉单值 industry 列
stock_industry   (code, industry_name, rank INT, is_primary BOOL)             -- 多对多，rank 定「最相关前3」
chan_structure   (code, kl_type, autype, structure JSONB, updated_at)          -- 已确认 bi/seg/zs
bsp_index        (code, kl_type, autype, bsp_date, bsp_type, is_buy, price, time_key)  -- 买卖点索引
chan_snapshot    (code, kl_type, autype, pickle BYTEA, updated_at)             -- 续算基线快照
watchlist_folder (id PK, name, created_at)
watchlist_item   (folder_id, code, added_at)
monitor          (id PK, code, kl_type, monitor_start_time, entry_price,
                  status, sold_price, sold_at, pnl_pct, created_at)            -- status: monitoring/completed
```

- DAO 全部 psycopg2 裸 SQL（对齐 `RecomputeCursor`），不引入 ORM。
- `chan_structure.structure` 用 JSONB 存 bi/seg/zs 的序列化几何（毫秒时间戳 + 极值价 + 类型标签，契约对齐 `chan-web-viewer` D2 的字段映射）。
- `chan_snapshot.pickle` 用 BYTEA 存整棵 `CChan` 的 pickle，作为续算起点。

### D2. 后端：`WebAPI/` 单 FastAPI + 按 capability 拆路由

```
WebAPI/
  app.py                # 组装 FastAPI，挂载各 router
  config.py             # PG/DSN、DuckDB 路径、数据源等环境配置
  stock_store.py        # stock / stock_industry DAO
  bsp_store.py          # chan_structure / bsp_index / chan_snapshot DAO
  watchlist_store.py    # watchlist_folder / watchlist_item DAO
  monitor_store.py      # monitor DAO
  incremental_engine.py # 增量续算引擎（D3）
  routers/{stocks,bsp,watchlist,monitor}.py
```

`chan-web-viewer` 落地时追加 `routers/klines.py`，谁先落地谁建 `app.py` 骨架。

### D3. 增量续算引擎（方案 (ii) 状态续算）

**机制**（复用 chan.py 原生能力，不改计算逻辑）：

```
首次接入某 (code, kl_type, autype)：
  读 DuckDB 全部 K 线 → CChan(trigger_step=True) 一次性算完
  → 已确认 bi/seg/zs 落 chan_structure，买卖点落 bsp_index
  → pickle 快照整棵 CChan 落 chan_snapshot（续算基线）

增量（新 K 线确认后）：
  读 chan_snapshot → chan_load_pickle 恢复 → trigger_load(新 K 线)
  → 只重算未确认尾部 → 新确认走势/新买卖点落 PG → 更新快照

日终：
  扫描当日有新增 K 线的股票 → 逐只执行增量 → 记录新买卖点到 bsp_index
```

**Spike（任务 #1，硬门）**：验证两点，任一不满足则回退「按股票全量重算」：
1. pickle 往返后 `trigger_load` 续算结果 == 从头全量重算结果（比对 bi/seg/zs/bsp 序列）。
2. 已确认前缀（`is_sure=True` 元素）在续算前后保持一致、不被污染。

- 回退路径：增量不可行时，退化为「某股票有新 K 线就整只全量重算」（省的是「只算有变化的股票」，非「股内增量」），接口/存储不变。

### D4. 买卖点索引与查询聚合

- `bsp_index` 一行 = 一个买卖点，`bsp_date` 用 `klu.time` 的日期（可建索引），`price` = 买点取 `klu.low`、卖点取 `klu.high`。
- 查询 `GET /api/bsp?kl_type=&date=&bsp_type=&is_buy=` → 按条件过滤命中股票；聚合 `GET /api/bsp/aggregate?` → 按 `stock_industry.industry_name`（取 `rank` 最小的主行业）GROUP BY 得板块买卖点分布。
- 日终批量写入用 `INSERT ... ON CONFLICT DO NOTHING`（按 `(code,kl_type,autype,bsp_date,bsp_type,is_buy,time_key)` 去重），避免重复记录。

### D5. 行业多对多与数据源

- 单行业数据源 BaoStock `query_stock_industry` 不满足「多标签」→ 换东财/akshare 的「所属行业 + 概念板块」。
- `stock_industry` 存全部行业，`rank` 记录数据源返回顺序（或主行业标记），列表/详情只取 `rank` 前 3。
- 行业数据在导入/日终同步时批量刷新；手动可增删。

### D6. 监控：卖点检测、买入价基准与结算

- **买入价** = 监控时所在买卖点信号价（买点 `klu.low`）；**盈利** = 百分比 `(现价 - 买入价)/买入价`。
- **卖点检测**：被监控股票按 `monitor.kl_type`，新 K 线触发续算时检查该周期是否出现卖点（`is_buy=False`），**任一类型卖点即卖**；卖出价 = 卖点信号价（`klu.high`）。
- **节奏**：日终批算为主（对齐「当天结束后」）；盘中实时推送作为后续可选优化（记入 Open Questions）。
- **结算**：卖出时写 `sold_price`/`sold_at`/`pnl_pct`，`status` 置 `completed`，转入监控完成页。
- **监控时间**：`monitor_start_time` 为加入监控的时间；「设置监控时间」解释为监控起始/结算截止的配置，具体语义见 Open Questions。

### D7. LLM 亏损归因

- 触发：监控完成页手动「大模型分析」按钮，仅对 `pnl_pct < 5%` 的标的。
- 输入：标的 + 周期 + K 线序列 + 缠论结构（bi/seg/zs/bsp）+ 买卖点特征（`CFeatures`）+ 买入/卖出/最终盈利。
- 输出：失败原因（缠论方法论失效 vs chan.py 计算逻辑错误）+ 关键证据，落库供列表/详情查看。
- 供应商与模型待定（Open Questions）；先定义输入/输出契约，供应商可插拔。

### D8. 前端：`web/` 单 SPA 三 Tab + 监控完成子页

```
web/
  /watchlist          自选：文件夹树 + 股票表格（名称/编码/股价/行业≤3）+ 增删改 + 批量加入
  /bsp                历史买卖点：查询表单（周期/日期/类型）+ 结果表（多选）+ 板块聚合 + 加入自选/监控
  /monitor            监控：列表 + 盈利走势折线（ECharts）+ 总体盈利
  /monitor/completed  监控完成：结算列表 + 大模型归因按钮 + 失败原因列表/详情
```

- 表格/表单用 Element Plus（CRUD 密集）；盈利走势折线用 ECharts（轻量时序，`web/package.json` 管理）。

### D9. 买卖点绩效统计（`bsp-performance`）

按 `(kl_type, bsp_type, is_buy)` 聚合 bsp_index 与 monitor 结算，产出样本数、胜率（`pnl_pct>0` 占比）、平均盈亏比。数据量小，先实时聚合（联查 bsp_index + monitor），不物化。端点 `GET /api/bsp/performance?kl_type=&bsp_type=`，附样本明细下钻。

### D10. 条件选股器（`stock-screener`）

`screener` 表存策略条件 JSONB（kl_type/date/bsp_type/is_buy/行业/指标阈值）；执行 = 翻译成对 bsp_index + stock + stock_industry + DuckDB（指标）的查询。定时跑放在日终流水线之后（可选）。端点：策略 CRUD `/api/screeners` + `POST /api/screeners/{id}/run`。

### D11. 区间套（多级别买卖点）

bsp_index 已含 `kl_type` 列，多级别查询天然支持：`GET /api/bsp/{code}?kl_types=K_DAY,K_60M,K_30M` 返回该股票各周期买卖点。前端叠加依赖 `chan-web-viewer` 的 K 线图（本变更只提供多级别数据接口），或本页加一个轻量多级别时间轴视图（可选）。

### D12. 预警提醒（`alerts`）

`alert` 表存规则（type: `price`/`bsp`/`monitor_sell` + 参数/阈值）。触发检查挂在日终流水线（续算/卖点检测时顺带检查），盘中实时为后续可选。**通知通道 = 站内信（Web 页面列表），首版仅站内信**；webhook/邮件/微信为后续可选扩展，非本变更范围。

### D13. 前端页面与字段清单

**页面清单（7 个页面，`web/` SPA）：**

| # | 页面 | 路由 | capability |
|---|------|------|------------|
| 1 | 我的自选 | `/watchlist` | watchlist |
| 2 | 历史买卖点 | `/bsp` | bsp-index |
| 3 | 股票监控 | `/monitor` | bsp-monitoring |
| 4 | 监控完成 | `/monitor/completed` | bsp-monitoring |
| 5 | 买卖点绩效 | `/performance` | bsp-performance |
| 6 | 条件选股 | `/screener` | stock-screener |
| 7 | 预警提醒 | `/alerts`（规则 + 站内通知子 tab） | alerts |
| 8 | 登录 | `/login` | auth |
| 9 | 权限管理 | `/system`（admin 专属） | auth |

**股票基本信息字段（stock 实体，各页复用）：** `code`、`name`、`exchange`、`price`（DuckDB 最新收盘）、`change_pct`（涨跌幅，可选增强）、`industries`（≤3 最相关行业）。

**各页面列表字段：**

- **`/watchlist` 自选**：左 = 文件夹树；右表 = `选择框 | 编码 | 名称 | 股价 | 涨跌幅 | 行业(≤3) | 操作(移出/移动文件夹)`。
- **`/bsp` 历史买卖点**：查询表单 = `周期 | 日期 | 买卖点类型 | 方向`；结果表（一行 = 一个买卖点记录）= `选择框 | 编码 | 名称 | 股价 | 行业(≤3) | 买卖点类型 | 方向 | 买卖点价格 | 买卖点日期 | 周期`（加入自选/监控时按 `code` 去重）；板块聚合表 = `行业 | 买点股票数 | 卖点股票数 | 合计`；区间套子面板 = 选中股票后横向列出各周期（日/60M/30M）买卖点。
- **`/monitor` 监控**：汇总卡 = `总体盈利(%) | 监控中数量`；表 = `编码 | 名称 | 周期 | 监控起始时间 | 买入价 | 现价 | 盈利% | 状态`；盈利走势折线（ECharts）。
- **`/monitor/completed` 监控完成**：表 = `编码 | 名称 | 周期 | 买入价 | 卖出价 | 卖出时间 | 最终盈利% | 归因状态 | 操作(大模型分析/查看详情)`；失败原因列表 + 详情；顶部「大模型分析」按钮（仅 `pnl_pct < 5%`）。
- **`/performance` 绩效**：筛选 = `周期 | 买卖点类型`；统计表 = `周期 | 类型 | 方向 | 样本数 | 胜率% | 平均盈亏% | 盈亏比`；样本明细 = `编码 | 名称 | 日期 | 盈亏%`。
- **`/screener` 选股**：策略列表 = `策略名 | 条件摘要 | 更新时间 | 操作(执行/编辑/删除/新建)`；执行结果 = `编码 | 名称 | 股价 | 行业(≤3) | 匹配指标`。
- **`/alerts` 预警**：规则子 tab = `类型(价格/买卖点/监控卖点) | 目标 | 阈值/参数 | 状态 | 创建时间 | 操作`；站内通知子 tab = `时间 | 类型 | 内容 | 关联股票 | 已读状态`。

**统计信息基本字段：** 板块聚合 = `行业 | 买点股票数 | 卖点股票数 | 合计`；绩效 = `样本数 | 胜率% | 平均盈亏% | 盈亏比`；监控 = `总体盈利(%) | 盈利走势时序`。

**区间套**：不单独开页，作为 `/bsp` 子面板；本变更只提供多级别买卖点数据 + 轻量时间轴，K 线图叠加留给 `chan-web-viewer`。

### D14. 页面交互细化

**通用约定：** 顶部导航栏含 7 个菜单 + 面包屑；组件用 Element Plus（表格/表单/弹窗/Drawer/消息/分页/switch）；列表服务端分页（默认 20/页）；搜索输入防抖 300ms；异步操作 loading 骨架屏；空态 `el-empty` + 引导文案；失败 `ElMessage.error`。

**1. `/watchlist` 自选**
- 左 = 文件夹树（新建/重命名/删除，删除含股文件夹需二次确认），右 = 表格随选中文件夹刷新。
- 顶部虚拟「全部」节点 = 跨文件夹去重视图。
- 股票行操作：移出自选、移动到其他文件夹（下拉选择）。
- 添加入口：`/bsp` 批量加入（主入口），或手动搜索股票加入。
- 股价/涨跌幅列可排序。

**2. `/bsp` 历史买卖点**
- 查询表单（周期/日期/类型/方向）+「查询」「重置」；结果表多选 + 服务端分页。
- 「板块聚合」tab：按第一行业聚合，点行业行回填筛选该行业。
- 批量加入自选：选中 → 弹窗（文件夹名默认 = 查询日期，可改）→ 确认 → 返回「新增 N 只」。
- 加入监控：选中 → 弹窗（周期默认 = 查询周期、监控时间可设）→ 确认落 `monitor`。
- 区间套：行内「区间套」按钮 / 双击 → Drawer 展示多级别（日/60M/30M）买卖点时间轴。

**3. `/monitor` 监控**
- 顶部汇总卡：总体盈利%、监控中数量。
- 盈利走势折线（ECharts）可切换「汇总 / 单只」。
- 表格实时盈利%；后端自动结算后该行转完成页；可选手动结束监控。

**4. `/monitor/completed` 监控完成**
- 顶部「大模型分析」按钮：对 `pnl<5%` 且未归因标的批量触发，显示进度。
- 归因状态列：未归因 / 归因中 / 已归因。
- 点「查看详情」弹窗展示归因结果（失败原因分类 + 证据）。
- 失败原因汇总区：列出全部 <5% 标的失败原因，可跳详情。

**5. `/performance` 绩效**
- 筛选（周期/类型/方向）→ 统计表。
- 点某行 → Drawer 下钻样本明细（股票/日期/盈亏）。
- 可选胜率对比柱状图（ECharts）。

**6. `/screener` 选股**
- 策略列表 + 「新建策略」；新建/编辑走表单弹窗（周期/日期/类型/方向/行业/指标阈值）。
- 「执行」→ 后端扫描（长耗时给进度提示）→ 结果表（编码/名称/股价/行业/匹配指标），可批量加入自选。
- 删除策略二次确认。

**7. `/alerts` 预警**
- 子 tab「预警规则 / 站内通知」。
- 规则：新建/编辑/删除/启停（switch）；新建表单（类型 = 价格/买卖点/监控卖点 + 目标/阈值）。
- 通知：未读高亮，单条/全部已读；点通知跳转关联股票。

### D15. 页面模块与字段拆解（模块化细化，字段以本节为准）

#### 1. `/watchlist` 我的自选

| 模块 | 字段 / 内容 |
|------|-------------|
| 文件夹树（左） | 文件夹名、股票数；操作：新建/重命名/删除/切换 |
| 顶部工具条 | 搜索框（名称/编码，防抖）、「添加股票」「批量移出」按钮 |
| 自选股票表格（右） | 选择框、编码、名称、股价、涨跌幅、行业(≤3)、操作（移出/移动到文件夹） |
| 加入自选弹窗（跨页） | 文件夹名（默认 = 日期，可改） |

#### 2. `/bsp` 历史买卖点

| 模块 | 字段 / 内容 |
|------|-------------|
| 查询筛选区 | 周期类型、日期、买卖点类型、方向(买/卖)、「查询」「重置」 |
| 操作工具条 | 「批量加入自选」「加入监控」（基于多选） |
| 结果表 | 选择框、编码、名称、股价、行业(≤3)、买卖点类型、方向、买卖点价格、买卖点日期、周期、操作（区间套） |
| 板块聚合区 | 行业、买点股票数、卖点股票数、合计；点行业行回填筛选 |
| 区间套 Drawer | 周期(日/60M/30M)、买卖点列表（类型、方向、价格、日期） |

#### 3. `/monitor` 股票监控

| 模块 | 字段 / 内容 |
|------|-------------|
| 汇总卡 | 总体盈利(%)、监控中数量 |
| 盈利走势折线图 | 时间轴、盈利%(时序)；切换「汇总 / 单只」 |
| 监控列表表格 | 编码、名称、周期、监控起始时间、买入价、现价、盈利%、状态、操作（手动结束） |
| 筛选 | 搜索框（名称/编码） |

#### 4. `/monitor/completed` 监控完成

| 模块 | 字段 / 内容 |
|------|-------------|
| 操作工具条 | 「大模型分析」按钮（批量触发 pnl<5%）、进度提示 |
| 完成列表表格 | 编码、名称、周期、买入价、卖出价、卖出时间、最终盈利%、归因状态、操作（查看详情/重新分析） |
| 失败原因汇总区 | 编码、名称、失败原因分类、最终盈利%、操作（查看详情） |
| 归因详情弹窗 | 失败原因分类（缠论失效/计算逻辑错误）、证据、输入摘要、盈亏 |

#### 5. `/performance` 买卖点绩效

| 模块 | 字段 / 内容 |
|------|-------------|
| 筛选区 | 周期、买卖点类型、方向 |
| 绩效统计表 | 周期、类型、方向、样本数、胜率%、平均盈亏%、盈亏比 |
| 样本明细 Drawer | 编码、名称、日期、盈亏% |
| 胜率对比图（可选） | 类型(x)、胜率%(y)，柱状图 |

#### 6. `/screener` 条件选股

| 模块 | 字段 / 内容 |
|------|-------------|
| 策略列表 | 策略名、条件摘要、更新时间、操作（执行/编辑/删除）+「新建策略」 |
| 策略表单弹窗 | 策略名、周期、日期、买卖点类型、方向、行业、指标阈值 |
| 扫描进度 | 进行中状态、耗时 |
| 扫描结果表 | 编码、名称、股价、行业(≤3)、匹配指标、操作（加入自选） |

#### 7. `/alerts` 预警提醒

| 模块 | 字段 / 内容 |
|------|-------------|
| 子 tab | 预警规则 / 站内通知 |
| 规则列表（tab1） | 类型(价格/买卖点/监控卖点)、目标(股票/条件)、阈值/参数、状态(启用/停用 switch)、创建时间、操作（编辑/删除）+「新建规则」 |
| 规则表单弹窗 | 类型、目标股票、阈值/参数、启用状态 |
| 通知列表（tab2） | 时间、类型、内容、关联股票、已读状态、操作（标记已读）+「全部已读」 |

### D16. 多用户认证与 RBAC 权限

**认证**：用户名 + 密码，passlib[bcrypt] 哈希；JWT（python-jose）签发 `access_token`，经 `Authorization: Bearer` 携带。端点 `POST /api/auth/login`（返回 token + user）、`GET /api/auth/me`（返回 user + 权限 code 列表）、`POST /api/auth/logout`。

**RBAC 数据模型（PG）：**

```sql
app_user        (id PK, username UNIQUE, password_hash, display_name,
                 role_id FK, enabled BOOL, created_at)
role            (id PK, name, code UNIQUE, is_admin BOOL, created_at)
permission      (id PK, code UNIQUE, name, type VARCHAR('menu'|'button'))
role_permission (role_id, permission_id)   -- 多对多
```

- 用户单角色（`app_user.role_id`），角色多权限（`role_permission`）。
- **admin 绝对权限**：内置 `role.code='admin'`（`is_admin=true`），不可删、不可改权限；后端 `require_perm` 对 admin 直接放行，前端 admin 渲染全部菜单/按钮。

**权限 code 约定（`permission` 表种子数据）：**

- 菜单 `menu:*`：`watchlist` / `bsp` / `monitor` / `performance` / `screener` / `alerts` / `system`（决定菜单/页面可见性）
- 管理 `manage`：单一管理权限，决定是否可执行管理类操作（增删改/删除/启停/重置密码/角色配置/系统管理）
- **业务按钮（查询/加入自选/加入监控/区间套/大模型分析/执行选股/标记已读等）对登录用户全部开放，不做按钮级校验**

**后端鉴权**：FastAPI `Depends(get_current_user)` 解析 token → `require_perm(code)` 校验权限（admin 放行），无权限返回 403。业务路由按需挂 `require_perm`。

**前端**：
- `/login` 登录页；`pinia` auth store 存 token（localStorage）/user/perms。
- 路由守卫：未登录跳 `/login`；已登录但无 `menu:*` 权限的菜单隐藏，直接访问无权限路由 → 403 页。
- `v-permission="'manage'"` 指令仅控制「管理类按钮」显隐；业务按钮全部开放；admin 全部可见。

**权限管理页 `/system`（admin 专属）：**

| 模块 | 字段 / 内容 |
|------|-------------|
| 用户管理 | 用户名、显示名、角色、状态(启用/停用)、创建时间、操作（编辑/重置密码/启停/删除） |
| 角色管理 | 角色名、code、是否 admin、操作（编辑/删除；admin 内置不可删改） |
| 角色-权限配置 | 选角色 → 勾选菜单权限（`menu:*`）+ 管理权限（`manage`）→ 保存 |

**登录页 `/login`：** 用户名、密码、「登录」；登录失败提示。

**页面总数 7 → 9：** 新增 `/login`（auth）、`/system`（auth，admin 专属）。

## Risks / Trade-offs

- **[增量续算正确性（最大风险）]** pickle 往返 + `trigger_load` 续算可能污染已确认前缀 → spike 硬门，失败回退全量重算（D3）。
- **[快照体积/一致性]** pickle 整棵 CChan 体积大、与业务数据分处两类存储 → 存 PG BYTEA 与 chan_structure 同事务，避免半新半旧；必要时压 pg 大对象或磁盘。
- **[DuckDB 单写锁]** 续算读 K 线时可能撞灌数写 → read-only 短连接 + 日终错峰。
- **[全市场扫描量级]** ~5000 只 × 多周期，首次全量建索引耗时数小时 → 复用 `download_kl.py` 批处理/分批 + 游标水位，可续跑。
- **[行业数据源变更]** 东财/akshare 多标签接口受限频、口径差异 → 尽力填充、rank 兜底，失败不阻断。
- **[LLM 依赖]** 外部调用成本/稳定性/幻觉 → 仅手动触发、结果只作归因参考并落库，不做自动交易决策。
- **[与 chan-web-viewer 目录共享]** → 路由/页面模块化，谁先落地谁建骨架。

## Migration Plan

纯新增为主，`stock` 表仅去掉 `industry` 单值列（迁移到 `stock_industry`）：

1. 建 PG 新表（`stock_industry`/`chan_structure`/`bsp_index`/`chan_snapshot`/`watchlist_*`/`monitor`），`stock` 表迁走 `industry`。
2. **Spike**：验证 pickle 往返 + `trigger_load` 续算正确性（D3），决定走 (ii) 还是回退全量重算。
3. 增量续算引擎 + 首次全量建索引（分批）。
4. 行业数据源接入 + `stock_industry` 填充。
5. `WebAPI/` 路由（stocks 已有 → bsp → watchlist → monitor）。
6. `web/` 三 Tab + 监控完成页，联调。
7. 日终流水线（新 K 线 → 续算 → 记录新买卖点 → 卖点检测/结算）。

回滚：删除新增 PG 表与 `WebAPI/`、`web/` 新增文件；`stock` 表 industry 迁移可逆（保留原列或备份）。计算路径零残留。

## Open Questions

- **监控时间语义**：`monitor_start_time` 之外，「设置监控时间」是否含一个结束/结算截止时间，需澄清。
- **监控调度节奏**：日终批算 vs 盘中实时（当前默认日终，盘中为后续优化）。
- **LLM 供应商/模型与输入裁剪**：供应商待定；输入契约已定（D7），具体 prompt/字段裁剪实现期定。
- **行业「最相关前 3」的排序信号**：数据源返回顺序 vs 主行业标记 vs 市值/概念热度，实现期定。
- **快照存储介质**：PG BYTEA vs 磁盘（权衡体积与一致性），spike 后定。
