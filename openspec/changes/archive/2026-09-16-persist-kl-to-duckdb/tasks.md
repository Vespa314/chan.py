## 1. 依赖与存储层

- [x] 1.1 在 `Script/requirements.txt` 新增 `duckdb`、`exchange_calendars`、PG 驱动（`psycopg2` 或 `sqlalchemy`），验证 `pip install -r Script/requirements.txt` 成功
- [x] 1.2 新建 `DataAPI/KLineStore.py`，建 `kline` 表（复合主键 code/kl_type/autype/time_key + OHLCV 字段），验证建表成功且 schema 与 design.md D2 一致
- [x] 1.3 在 KLineStore 实现 upsert（`INSERT OR REPLACE`）与 query(code, kl_type, autype, begin, end)，验证同一键重复写入仅剩一行、区间查询只返回范围内数据

## 2. 读适配器

- [x] 2.1 新建 `DataAPI/DuckDBAPI.py`，类 `CDuckDB` 继承 `CCommonStockApi`，实现 `get_kl_data`/`SetBasciInfo`/`do_init`/`do_close`，验证以 `data_src="custom:DuckDBAPI.CDuckDB"` 能逐根产出 K 线
- [x] 2.2 在 CDuckDB 内做 kl_type/autype 的 name↔enum 映射，验证从库读出的字符串能还原为对应枚举
- [x] 2.3 数据源可互换验证：同一股票/级别/区间分别用 BaoStock 与 DuckDB 源跑一遍，验证笔/段/买卖点结果一致

## 3. 灌数脚本（日线/盘后）

- [x] 3.1 新建 `Debug/download_kl.py`：拉取 → 校验 → upsert，默认增量（从 `max(time_key)` 续拉）并支持 `--full`，验证二次运行仅增量追加、无重复
- [x] 3.2 实现数据校验（OHLC 非法/时间乱序拒绝、异常跳变告警保留），验证非法行被拒绝、跳变行保留且触发告警
- [x] 3.3 实现 `--begin/--end` 区间重刷，验证仅删除并重写指定区间、其余历史保持不变
- [x] 3.4 用 `exchange_calendars` 实现缺口检测与交易日历，验证缺失交易日被检出、节假日不误判为缺口
- [x] 3.5 首次全历史回填分批续传，验证中断后重启从已入库最新 K 线续传

## 4. 配置与可观测

- [x] 4.1 新增配置文件（股票/级别/复权/轮询间隔/交易时段/存储路径），验证以配置文件驱动灌数、无需逐次命令行传参
- [x] 4.2 实现结构化日志、每股票状态水位、停更告警，验证股票最新 K 线时间在阈值内不推进时触发告警

## 5. 盘中接入与重算通知

- [x] 5.1 新增分钟级数据源适配器（Akshare/东财/新浪），验证能拉取 5min/30min 分钟 K 线
- [x] 5.2 实现盘中轮询引擎（1 分钟间隔、交易时段运行、只收已收盘 bar），验证形成中的 bar 被排除在持久化与计算之外
- [x] 5.3 实现水位通知与重算：新 bar 落库触发重算，`last_processed_time` 游标存 PG，验证新 bar 触发重算且游标落 PG（而非 DuckDB 文件）
- [x] 5.4 实现限频/指数退避/单股票失败隔离，验证单只股票失败不中断其余且按退避重试

## 6. 端到端集成验证

- [x] 6.1 端到端：下载 → 灌数 → 以 DuckDB 源离线跑 `CChan` 出买卖点，与 BaoStock 源同参数结果一致
