## Purpose

将原始 K 线持久化到本地 DuckDB 存储，并提供幂等灌数、断点续拉、数据校验、缺口补齐与盘中短周期接入，使缠论计算可离线从本地库读取 K 线，且与网络数据源结果一致。

## ADDED Requirements

### Requirement: 原始 K 线持久化
系统 SHALL 将原始 K 线持久化到本地 DuckDB 存储。每根 K 线 SHALL 由 `(code, kl_type, autype, time_key)` 唯一标识，并 SHALL 存储 open、high、low、close、volume、turnover、turnover_rate。

#### Scenario: 写入并读取一根 K 线
- **WHEN** 一根原始 K 线被写入存储
- **THEN** 可按其 OHLCV 与元信息原样读回

#### Scenario: 同一股票不同时间点为独立行
- **WHEN** 两根 K 线共享 code/kl_type/autype 但 time_key 不同
- **THEN** 它们被存储为两行独立记录

### Requirement: 幂等去重
系统 SHALL 在相同 `(code, kl_type, autype, time_key)` 被多次写入时不产生重复行，后一次写入 SHALL 覆盖前一次。

#### Scenario: 重复写入同一根 K 线
- **WHEN** 同一根 K 线（相同 code/kl_type/autype/time_key）被写入两次
- **THEN** 存储中仅保留一行，且为该键的最新值

### Requirement: 断点续拉与回填续传
灌数 SHALL 从已存储的最新 time_key 续拉而非重拉全历史；首次全历史回填 SHALL 分批进行且可中断续传。

#### Scenario: 已有数据时增量续拉
- **WHEN** 存储中已有截至时间 T 的 K 线
- **THEN** 下一次灌数从 T（含少量回看窗口）开始请求，而非从头开始

#### Scenario: 首次回填可中断续传
- **WHEN** 首次全历史回填中途被中断
- **THEN** 重启后从已入库的最新 K 线续传，而非重拉已完成的历史

### Requirement: 区间查询
系统 SHALL 支持按 code、kl_type、autype 与时间区间检索 K 线。

#### Scenario: 按日期区间读取
- **WHEN** 以 (code, kl_type, autype, begin, end) 查询
- **THEN** 仅返回 time_key 落在 [begin, end] 区间内的 K 线

### Requirement: 数据源可互换
从本地存储读取的 K 线 SHALL 与从网络数据源读取的 K 线可互换，下游分析结果 SHALL 完全一致。

#### Scenario: 本地库与网络源结果一致
- **WHEN** 同一 code/级别/日期区间分别经网络源与本地存储分析一次
- **THEN** 得到的笔/段/中枢/买卖点完全一致

### Requirement: 数据校验
系统 SHALL 拒绝结构性非法的 K 线（OHLC 关系非法、时间非单调），并 SHALL 对单根异常跳变的 K 线告警但保留。

#### Scenario: OHLC 非法拒绝
- **WHEN** 一根 K 线满足 high < low、high < max(open,close) 或 low > min(open,close)
- **THEN** 该 K 线被拒绝写入并触发告警

#### Scenario: 时间乱序拒绝
- **WHEN** 一根 K 线的 time_key 对同一 (code, kl_type, autype) 不严格递增
- **THEN** 该乱序 K 线被拒绝写入

#### Scenario: 异常跳变告警但不拒绝
- **WHEN** 一根 K 线的涨跌幅超过可配置阈值（如除权除息导致的真实跳空）
- **THEN** 该 K 线被保留并触发告警，但不被拒绝

### Requirement: 缺口检测与区间重刷
系统 SHALL 检测已存储历史中缺失的交易日，并 SHALL 支持对指定日期区间重刷。

#### Scenario: 检测历史缺口
- **WHEN** 已存储历史中缺失某个交易日
- **THEN** 该缺口被记录，并对该区间触发针对性补拉

#### Scenario: 区间重刷
- **WHEN** 对 [begin, end] 区间发起重刷
- **THEN** 仅该区间的数据被删除后重写，其余历史保持不变

### Requirement: 交易日历
系统 SHALL 使用交易日历（exchange_calendars）判定交易日与交易时段，并 SHALL 将其用于缺口检测与盘中"已收盘"判定。

#### Scenario: 节假日休市不误判
- **WHEN** 遇到节假日（非交易日）
- **THEN** 不将其视为缺口，且盘中调度不在该日轮询

### Requirement: 盘中只收已收盘 K 线
盘中灌数 SHALL 仅持久化并送入计算"收盘时刻 ≤ 当前时刻"的 K 线；正在形成的 K 线 SHALL 不进入计算。

#### Scenario: 未收盘 K 线不进计算
- **WHEN** 一根 5 分钟 K 线仍在形成中（其收盘时刻晚于当前时刻）
- **THEN** 它被排除在持久化与笔/买卖点计算之外

### Requirement: 盘中水位通知与重算
新 K 线落库后，系统 SHALL 触发最新分析结果的重算；重算的已处理时间游标 SHALL 存入 PostgreSQL 业务库，水位则从 DuckDB 存储派生。

#### Scenario: 新 K 线落库触发重算
- **WHEN** 一根或多根新收盘 K 线被写入
- **THEN** 重算进程被通知并产出更新后的分析结果

#### Scenario: 重算游标存 PostgreSQL
- **WHEN** 重算进程处理完新的 K 线并推进游标
- **THEN** 其已处理时间游标持久化到 PostgreSQL（而非写入 DuckDB 的 K 线文件）

### Requirement: 配置与可观测
系统 SHALL 支持通过配置文件配置股票列表、级别、复权、轮询间隔、交易时段、存储路径，并 SHALL 输出结构化日志、暴露每只股票的数据状态，并在反复失败或进度停滞时告警。

#### Scenario: 配置文件驱动
- **WHEN** 灌数以一份列明股票/级别/复权的配置文件运行
- **THEN** 它仅处理这些条目，无需逐次命令行传参

#### Scenario: 数据停更告警
- **WHEN** 某股票最新 K 线时间在可配置时长内未推进
- **THEN** 触发告警

### Requirement: 限频 / 退避 / 失败隔离
系统 SHALL 对请求限速、对失败请求按指数退避重试，并 SHALL 按单只股票隔离失败，使单只股票失败不中断其余股票。

#### Scenario: 单股票失败不影响其他
- **WHEN** 拉取某只股票失败
- **THEN** 其余股票继续灌数，且失败请求按退避策略重试
