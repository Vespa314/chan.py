## 1. 共享枚举与行业数据源

- [ ] 1.1 抽 `DataAPI/StockUniverse.py`，迁入 `is_a_share_stock`/`query_all_a_share`/`latest_trading_day`，`Debug/gen_stock_list.py` 改为调用共享模块；验证：`PYTHONPATH=. python Debug/gen_stock_list.py --limit 20` 输出与重构前等价（A 股过滤、交易所分布一致）。
- [ ] 1.2 接入多行业数据源（东财/akshare），返回每只股票的行业与概念标签及顺序；验证：对样本股票能返回 ≥1 个行业标签，且标签顺序可作 rank 依据。
- [ ] 1.3 新增共享的灌数配置拼装函数（`to_ingest_config`）；验证：生成 JSON 与 `Debug/ingest_config.example.json` 同构、可被 `IngestUtil.load_config` 读取。

## 2. 存储层（PG schema + DAO）

- [ ] 2.1 实现 `WebAPI/stock_store.py`：`stock` 表 DDL（去单值 industry）+ 幂等 upsert/`list`/`get`/`delete` + `stock_industry` 表（多对多，`rank`/`is_primary`）；验证：建表成功，同 `code` 二次 upsert 不重复，行业多对多读写、按 `rank` 取前 3。
- [ ] 2.2 实现 `WebAPI/bsp_store.py`：`chan_structure`(JSONB)/`bsp_index`/`chan_snapshot`(BYTEA) 三表 DDL + DAO；验证：结构 JSONB 往返无损，`bsp_index` 幂等写入去重，快照 BYTEA 存取成功。
- [ ] 2.3 实现 `WebAPI/watchlist_store.py` + `WebAPI/monitor_store.py`：`watchlist_folder`/`watchlist_item`、`monitor` 表 DDL + DAO；验证：文件夹增删、monitor 状态流转 `monitoring → completed` 正确。

## 3. 增量续算引擎（spike 先行）

- [ ] 3.1 Spike：对样本股票验证 pickle 往返 + `trigger_load` 续算结果 == 从头全量重算结果（比对 bi/seg/zs/bsp 序列），且 `is_sure=True` 已确认前缀在续算前后一致；验证：diff 一致则走 (ii)，否则记录回退结论。
- [ ] 3.2 实现 `WebAPI/incremental_engine.py` 首次接入：读 DuckDB 全部 K 线 → `trigger_step=True` 全量算 → 已确认结构落 `chan_structure`、买卖点落 `bsp_index`、pickle 快照落 `chan_snapshot`；验证：单只股票产出完整已确认结构 + 快照。
- [ ] 3.3 实现增量续算：读 `chan_snapshot` → `chan_load_pickle` → `trigger_load` 新 K 线 → 只算未确认尾部 → 落新确认结构/新买卖点 → 更新快照；验证：续算结果与全量重算一致。
- [ ] 3.4 日终流水线：扫描当日有新增 K 线的股票批量续算并记录新买卖点到 `bsp_index`；验证：日终后 `bsp_index` 新增当日买卖点且无重复。

## 4. 买卖点索引查询与聚合

- [ ] 4.1 实现 `GET /api/bsp`：按 `kl_type`/`date`/`bsp_type`/`is_buy` 查询命中股票；验证：条件过滤返回正确股票集合。
- [ ] 4.2 实现 `GET /api/bsp/aggregate`：按主行业（`rank` 最小）GROUP BY 得板块买卖点分布；验证：板块聚合结果与逐股票结果吻合。

## 5. 后端 stocks 路由（沿用）

- [ ] 5.1 建 `WebAPI/app.py` + `config.py` 骨架并挂载各 router；验证：`uvicorn` 启动后 `GET /docs` 可达。
- [ ] 5.2 实现 `routers/stocks.py` CRUD（列表/详情/upsert/编辑/删除 + `q`/`exchange`/`industry`/`enabled` 筛选分页）；验证：增删改查与筛选分页正确，行业筛选走多对多匹配。
- [ ] 5.3 实现 `POST /api/stocks/import`：全市场枚举 + 行业填充 + 去重 upsert；验证：返回 `{imported, skipped}`，已存在 code 不被覆盖，指数/B 股/基金被排除。
- [ ] 5.4 实现 `GET /api/stocks/status`：read-only DuckDB `max(time_key)` + `RecomputeCursor` 水位 + 日历/停更阈值；验证：返回 `last_time_key`/`gap`/`stale`。
- [ ] 5.5 实现 `GET /api/stocks/export-config`：启用标的展开为 `stocks` 数组套灌数骨架；验证：输出可被 `download_kl.py --config` 消费。

## 6. 自选（watchlist）

- [ ] 6.1 实现 `routers/watchlist.py`：文件夹 CRUD + 切换查看 + 批量加入自选（默认日期作文件夹名、可改）；验证：文件夹增删、批量加入、切换查看正确。
- [ ] 6.2 自选列表接口返回名称/编码/股价（DuckDB 最新收盘）/行业≤3；验证：字段齐全、行业最多 3 个。

## 7. 监控、卖点检测与 LLM 归因

- [ ] 7.1 实现 `routers/monitor.py` 加入监控：记录周期、监控时间、买入价（买点 `klu.low`）；监控列表返回基本信息 + 盈利走势 + 总体盈利（百分比）；验证：加入监控后列表与盈利计算正确。
- [ ] 7.2 卖点检测：续算时检查监控周期是否出现卖点（`is_buy=False`），任一卖点即自动卖出（卖出价 `klu.high`）→ 结算 `pnl_pct` → `status=completed`；验证：出现卖点的监控股票被自动结算并转完成页。
- [ ] 7.3 LLM 归因：对 `pnl_pct < 5%` 的完成标的调用大模型，输出失败原因（缠论失效 vs 计算逻辑错误）+ 证据并落库，支持详情；验证：归因结果落库并可查看详情。

## 8. 前端三 Tab + 监控完成页

- [ ] 8.1 建 `web/` 骨架 + 路由 `/watchlist`、`/bsp`、`/monitor`、`/monitor/completed` + Element Plus + ECharts；验证：`npm run dev` 后各路由可访问。
- [ ] 8.2 自选页：文件夹树 + 股票表格 + 增删改 + 批量加入；验证：CRUD 联动后端、切换文件夹正确。
- [ ] 8.3 历史买卖点页：查询表单 + 结果表多选 + 板块聚合 + 加入自选/监控；验证：查询→聚合→加入自选→加入监控全流程可用。
- [ ] 8.4 监控页 + 完成页：监控列表 + 盈利走势折线 + 总体盈利 + 归因按钮 + 失败原因列表/详情；验证：监控→结算→归因全流程可用。

## 9. 初始化与端到端

- [ ] 9.1 提供从 `Debug/ingest_config.all_stocks.json` 灌入初始股票池 + 行业填充的脚本；验证：股票池与 `stock_industry` 有数据。
- [ ] 9.2 端到端冒烟：灌数 → 建买卖点索引 → 查买卖点 → 加自选 → 监控 → 卖点结算 → LLM 归因；验证：全链路无报错、数据在各表正确落地。

## 10. 买卖点绩效统计

- [ ] 10.1 实现 `GET /api/bsp/performance`：按 `kl_type`/`bsp_type`/`is_buy` 聚合 bsp_index + monitor 结算，输出胜率/盈亏比/样本数；验证：统计结果与样本明细吻合。
- [ ] 10.2 实现样本明细下钻接口；验证：可下钻到具体股票、日期与盈亏。

## 11. 条件选股器

- [ ] 11.1 实现 `screener` 表 + 策略 CRUD（条件 JSONB）；验证：策略保存、复用、编辑、删除正确。
- [ ] 11.2 实现 `POST /api/screeners/{id}/run`：翻译条件执行扫描（bsp_index + stock + stock_industry + DuckDB 指标）；验证：返回满足全部条件的股票。

## 12. 区间套（多级别买卖点）

- [ ] 12.1 实现 `GET /api/bsp/{code}?kl_types=...`：返回该股票多周期买卖点；验证：多级别买卖点返回正确。
- [ ] 12.2 前端多级别买卖点叠加视图（或对接 `chan-web-viewer` K 线图）；验证：多级别买卖点可见。

## 13. 预警提醒

- [ ] 13.1 实现 `alert` 表 + 规则 CRUD（`price`/`bsp`/`monitor_sell`）；验证：规则保存并生效。
- [ ] 13.2 在日终流水线挂触发检查 + 站内通知；验证：满足条件的规则生成通知。

## 14. 用户认证与 RBAC 权限

- [ ] 14.1 建 `app_user`/`role`/`permission`/`role_permission` 表 + 种子权限（`menu:*` 7 项 + 单一 `manage`）+ 内置 admin 角色；验证：建表成功、admin 存在且 `is_admin=true`。
- [ ] 14.2 实现 `auth_store.py` + JWT 登录（`POST /api/auth/login`、`GET /api/auth/me`、`POST /api/auth/logout`，passlib[bcrypt]）；验证：登录返回 token、错误密码 401、`/me` 返回权限 code 列表。
- [ ] 14.3 实现依赖注入 `get_current_user` + `require_perm(code)`（admin 放行、无权限 403）并挂到业务路由；验证：无权限接口返回 403。
- [ ] 14.4 前端 `/login` + `pinia` auth store + 路由守卫 + `v-permission` 指令 + 动态菜单；验证：未登录跳登录、无权限菜单/按钮隐藏、直接访问无权限路由进 403。
- [ ] 14.5 实现 `/system` 权限管理页（用户管理、角色管理、角色-权限配置）；验证：用户/角色 CRUD 与权限分配生效。
