## Why

chan.py 已能计算缠论结构（分型/笔/线段/中枢/买卖点），K 线也已持久化到 DuckDB，但「选股 → 跟踪 → 复盘」这条链路上仍是断裂的：买卖点只现算、不落库，查询「某日全市场出现某买卖点的股票」得现算全市场（数小时）；没有自选分组、没有监控盈利跟踪、没有对亏损的归因复盘。需要一个股票管理 Web 页面，把「我的自选 / 历史买卖点 / 股票监控」串成闭环，并配套一个增量续算引擎把缠论结论（买卖点）落库，让查询与板块聚合退化成 SQL、让监控能按周期自动判定卖点。

## What Changes

- **增量续算引擎**：把已确认的缠论走势（笔/线段/中枢，`is_sure`）持久化到 PG（JSONB）作为「实体线」基线；新 K 线经 `trigger_step` 状态续算（pickle 快照已确认前缀 + `trigger_load` 追加新 K 线），只重算未确认尾部；交易日结束后把新出现的买/卖点记录到 PG 买卖点索引表。**先做 spike 验证 pickle 往返 + 续算正确性，失败回退全量重算。**
- **Tab1 我的自选**：文件夹分类自选股票、切换查看；每只股票展示名称、编码、股价、所属行业（最多 3 个）。
- **Tab2 历史买卖点**：按周期类型 / 日期 / 买卖点类型查询全市场命中股票；按行业聚合统计板块买卖点；查询结果多选后批量加入自选（默认以日期作文件夹名、可改）；多选后点击监控、设置监控时间。
- **Tab3 股票监控**：监控列表（基本信息 + 监控周期）+ 每只盈利走势折线 + 总体盈利点数；后端按监控周期用缠论逻辑检测卖点，任一卖点出现即自动标记卖出、标记监控完成、结算最终盈利；监控完成页提供大模型分析，对盈利 < 5% 的标的做亏损归因（缠论失败 vs 计算逻辑错误），可查看详情。
- **行业多对多**：股票可关联多个行业（不限额），页面展示最相关的前 3 个；行业数据落 PG。
- **分析增强**：买卖点绩效统计（各 BSP 类型历史胜率/盈亏比）、条件选股器（可保存复用的选股策略）、区间套（多级别买卖点查询）、预警提醒（价格/买卖点/监控卖点触发通知）。
- **多用户与权限**：多用户认证（登录/登出、JWT 会话），RBAC 权限控制（菜单权限 + 按钮权限），用户/角色管理与权限分配，admin 角色拥有绝对权限；配套登录页与权限管理页。
- **存储分工**：原始 K 线继续落 DuckDB；缠论结论 / 买卖点索引 / 行业 / 自选 / 监控落 PG。
- **不修改** `CChan`/`CBiList`/`CSegListChan`/`CZSList`/`CBSPointList` 的计算逻辑；续算仅复用其 `trigger_step` 与 pickle 能力。

## Capabilities

### New Capabilities

- `bsp-index`: 买卖点索引与增量续算能力。覆盖已确认缠论走势持久化、新 K 线增量重算未确认尾部、日终买卖点索引、按周期/日期/类型查询、按行业聚合统计板块买卖点、多级别买卖点查询（区间套）。
- `watchlist`: 我的自选列表能力。覆盖文件夹分类与切换、股票字段（名称/编码/股价/行业≤3）展示、从买卖点查询结果批量加入自选。
- `bsp-monitoring`: 股票监控能力。覆盖监控列表与盈利走势、总体盈利、按周期卖点自动检测与卖出结算、监控完成与盈利 < 5% 标的的大模型亏损归因。
- `bsp-performance`: 买卖点绩效统计能力。覆盖按买卖点类型与周期统计历史胜率、盈亏比与样本数，辅助评估各买卖点信号有效性。
- `stock-screener`: 条件选股能力。覆盖把周期/日期/买卖点类型/行业/指标阈值组合为可保存、可复用的选股策略并执行扫描。
- `alerts`: 预警提醒能力。覆盖价格触发、买卖点出现、监控卖点等事件的规则设置与触发通知。
- `auth`: 用户认证与 RBAC 权限能力。覆盖登录/登出、JWT 会话、菜单权限控制与管理权限控制（业务按钮全开放）、用户/角色管理与权限分配、admin 绝对权限。

### Modified Capabilities

- `stock-universe`: 行业从「可空单值」改为「多对多、不限额、展示前 3」，相应调整行业筛选与元数据模型。

## Impact

- **新增文件**：`WebAPI/`（在 stocks 路由基础上新增 bsp/自选/监控路由 + 续算引擎模块）、`web/`（新增 `/watchlist`、`/bsp`、`/monitor` 三个视图）、增量续算引擎（pickle 快照 + `trigger_load` 续算 + 日终买卖点索引）、PG schema 扩展（`stock_industry`/`chan_structure`/`bsp_index`/`watchlist_*`/`monitor*` 等表）、认证与权限（`auth_store.py` + `routers/{auth,system}.py` + `app_user`/`role`/`permission`/`role_permission` 表 + `/login`、`/system` 视图）。
- **修改文件**：`DataAPI/StockUniverse.py`（枚举逻辑 + 新增行业数据源接入）、`WebAPI/stock_store.py`（行业 M2M）、`Script/requirements.txt`（FastAPI/uvicorn，及 LLM SDK 待定）。
- **复用**：`persist-kl-to-duckdb` 的 DuckDB `kline`（原始 K 线源）；`chan-web-viewer` 的 FastAPI/uvicorn + Vue3+Vite+TS 栈；chan.py 的 `trigger_step`/`trigger_load`/`chan_dump_pickle`/`chan_load_pickle`（续算基底）。
- **依赖**：行业多标签数据源（东财/akshare）；LLM 供应商（待定，见 design Open Questions）；预警通知通道（先站内，webhook 后续）；认证依赖 JWT（python-jose）+ passlib[bcrypt]。
- **关联**：为 `chan-web-viewer` 的「搜索标的」backlog 提供行业/股票池基础；买卖点索引同时是后续策略/回测的选股数据源；区间套的多级别买卖点数据可被 `chan-web-viewer` 的 K 线图叠加消费。
