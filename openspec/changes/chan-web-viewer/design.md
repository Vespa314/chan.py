## Context

动机见 proposal.md - Why。这里只列决定方案所需的状态与约束。

- chan.py 计算流水线对数据来源无感知，`CChan` 门面按 `(code, KL_TYPE, config)` 现算，结果通过 `chan[KL_TYPE].bi_list / seg_list / zs_list / segzs_list / bs_point_lst / seg_bs_point_lst` 访问（见 [KLine/KLine_List.py:97-105](KLine/KLine_List.py#L97-L105)）。
- 已完成变更 `persist-kl-to-duckdb` 提供了 DuckDB 离线数据源 `custom:DuckDBAPI.CDuckDB`，可作为在线 BaoStock 的替代。
- 每个缠论对象都锚定到 `CKLine_Unit`，而 `CKLine_Unit.time` 是 `CTime`，已缓存秒级时间戳 `time.ts`（见 [Common/CTime.py:92](Common/CTime.py#L92)）。
- 关键对象字段（已核实）：`CBi` 的 `get_begin_klu()/get_end_klu()/get_begin_val()/get_end_val()/dir/is_sure`；`CSeg` 同构；`CZS` 的 `begin/end/low/high/mid`；`CBS_Point` 的 `klu/is_buy/type`。

## Goals / Non-Goals

**Goals:**
- 后端把 chan.py 已算好的缠论结构序列化成前端可消费的 JSON，前端用 KLineChart 以指定样式渲染。
- 支持单级别周期切换、副图指标开关、缩放/平移/十字光标、历史增量加载等功能。

**Non-Goals:**
- 不实现背驰标记（BI/XD/PZ/QS）检测与可视化（开源版无此判定，独立工作线）。
- 不实现搜索标的、保存布局（PG）、画图工具（工具栏）、图表设置面板——均记入 backlog。
- 不改动任何缠论计算逻辑与配置系统。

## Decisions

### D1. 后端形态：FastAPI 薄封装 `CChan`

后端只做「接收 `(symbol, period)` → 用 `CChan` 现算 → 读结果序列化 JSON」，包含缠论计算。`CChan` 的 `__getitem__` 已把结果按 `KL_TYPE` 暴露， `bi_list/seg_list/zs_list/segzs_list/bs_point_lst` 序列化。

- 增加在 CChan 内部加序列化方法。
- 使用「独立计算服务 / 缓存层」：把该股票缠论计算结果的**稳定前缀**（未确认/虚元素之前的已确认笔/线段/中枢/买卖点）缓存至 PG，键 = 股票标识 + 分析周期；未确认尾部不落缓存，随新 K 线重算。

### D2. 序列化契约：毫秒时间戳 + 极值价格 + 类型标签

JSON 顶层结构（一次请求返回一个 `(symbol, period)` 的完整结果）：

```jsonc
{
  "klines": [ { "timestamp": 1609459200000, "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 100000 } ],
  "bi":     [ { "begin": {"t": 1609459200000, "v": 9.0}, "end": {"t": 1610000000000, "v": 11.0}, "dir": "UP", "is_sure": true } ],
  "seg":    [ /* 同 bi 结构 */ ],
  "zs":     [ { "begin_t": 1609459200000, "end_t": 1610000000000, "low": 9.5, "high": 10.5, "mid": 10.0 } ],
  "seg_zs": [ /* 同 zs 结构 */ ],
  "bsp":    [ { "t": 1609459200000, "v": 9.0, "is_buy": true, "types": ["1"] } ]
}
```

字段映射规则（已按源码核实）：

| 对象 | 来源 | 说明 |
|------|------|------|
| `klines[].timestamp` | `klu.time.ts * 1000` | `CTime.ts` 是秒级 float，前端要毫秒 |
| `bi[].begin/end` | `get_begin_klu()/get_end_klu().time.ts` + `get_begin_val()/get_end_val()` | 笔端点 = 分型极值 K 线 + 极值价 |
| `seg[]` | 同 `bi`，经 `CSeg.get_begin_klu()` 等 | 线段端点 |
| `zs[].begin_t/end_t` | `CZS.begin/end`（`CKLine_Unit.time.ts`） | 中枢横跨时间 |
| `zs[].low/high/mid` | `CZS.low/high/mid` | 中枢区间 |
| `bsp[].v` | `klu.low if is_buy else klu.high` | 买点落分型低点、卖点落高点 |
| `bsp[].types` | `[x.value for x in point.type]` | `BSP_TYPE` 值：`1/1p/2/2s/3a/3b` |

**买卖点 UI 标签映射**（前端做，不改枚举）：`T1('1')→1B/1S`、`T2('2')→2B/2S`、`T2S('2s')→L2B/L2S`、`T3A/T3B('3a'/'3b')→3B/3S`、`T1P('1p')→PZ-B/PZ-S`。完整映射表最终以 UI 稿为准，阶段一先实现 `1B/2B/L2B/3B`（用户明确点名的买点）。

- 弃「时间戳存字符串」：前端 KLineChart 要求数值型毫秒时间戳，存数字更直接。
- 弃「把 `segseg_list`（线段的线段）也序列化」：单级别范围只画笔/线段，`segseg` 留作阶段 B（区间套）再暴露。

### D3. 数据源： DuckDB 离线源

后端经 `CChanConfig` 的 `data_src` 选择数据源使用`persist-kl-to-duckdb` 已完成，`custom:DuckDBAPI.CDuckDB` 作为离线源（避免重复在线拉取 + 限频）。后端启动时以配置项指定 `data_src`，不改计算路径。

### D4. 缠论全量返回，增量加载只针对 K 线

缠论（笔/线段/中枢/买卖点）是**递归结构，只能在完整历史上正确计算**，不能对部分窗口正确求值。因此：

- 后端对 `(symbol, period)` **一次算好、全量返回**缠论元素（每个元素按时间戳锚定）。
- 「拖到最左增量加载」针对的是 **K 线数据量**（短周期历史长时一次全量渲染贵）；前端经 KLineChart `setDataLoader` 的 `getBars('backward')` 请求更早 K 线。
- 缠论 overlay 按时间戳渲染，与「当前加载了哪些 K 线」解耦：前端拿到全量 overlay 后，无论视口内是哪些 K 线都能正确绘制。

阶段一因日线/常见周期数据量小（几千根），**先全量返回 K 线 + 缠论**；分页契约（`?end=<ts>` 返回更早 K 线）在接口签名上预留，作为短周期（1 分钟）历史过长时的优化路径，不阻塞阶段一。

### D5. 前端 overlay：KLineChart `registerOverlay` 自定义绘制

- **笔/线段**：自定义 overlay，`createPointFigures` 返回 `line` figure（两点折线）。
- **笔中枢/线段中枢**：矩形。KLineChart overlay 的 figure 类型需在探针阶段确认——若原生无 `rect` figure，则用 `polygon`（四点闭合）或两点 + `line` 组合实现半透明方框。
- **买卖点**：marker + 文本标签（`1B`/`L2B` 等），用 overlay 的文本/图标 figure 或独立的 annotation。

这正是「Tier 0 探针」要验证的核心不确定点：**KLineChart overlay 能否画出折线、矩形、带标签 marker 这三类图形**。探针用一段硬编码 JSON 驱动，先确认可行，再搭后端。

- 弃「用 ECharts 或 lightweight-charts」：见提案讨论，KLineChart 对金融场景 overlay/指标/交互更省事，且中文红涨绿跌原生对齐。

### D6. Vue 集成：chart 实例非响应式

KLineChart 是命令式 Canvas 库。chart 实例放在**普通变量**（非 `ref`），`onMounted` 里 `init`，`watch(current{symbol,period})` 触发命令式重载（`applyNewData` + 重画 overlay），`onBeforeUnmount` 里 `dispose`。避免把 Canvas 状态塞进 Vue 响应式代理（既慢又易错）。

### D7. 目录结构

- 后端：新增 `WebAPI/`（FastAPI 应用，含序列化模块 + 启动入口）。
- 前端：新增 `web/`（Vue3 + Vite + TypeScript，含 KLineChart 集成与 overlay 定义）。
- 前端依赖用 `web/package.json` 管理，与 `Script/requirements.txt`（Python）分离。

### D8. 缓存边界：只缓存稳定前缀，未确认尾部重算

缠论是递归结构，尾部元素（`is_sure == False` 的笔/线段、未确认买卖点）会随新 K 线到来而改变。因此缓存只落**稳定前缀**：

- **稳定前缀** = 截至最后一个 `is_sure == True` 元素为止的已确认元素（含其对应中枢/买卖点），不随未来 K 线改变，可安全缓存。
- 缓存键 = `(股票标识, 周期)`，并记录「最后已确认元素的时间戳」作水位游标。
- **未确认尾部**不落缓存，随新 K 线重算。
- 实现前提：计算服务需能从稳定前缀末尾**增量续算**（而非每次全量重算）。open-source `CChan` 的步进模式（`trigger_step=True`）逐根重算、具备「续算」语义，但能否以「缓存前缀 + 新 K 线」为起点恢复、且不改计算逻辑，需 spike 验证（见任务 3.2）。

### D9. 前端页面布局与模块

单页图表应用，无多 Tab。整体布局：

```
+--------------------------------------------------------------+
| 顶栏 TopBar                                                  |
|  [股票代码输入框]  [周期下拉]  [副图指标菜单]         [图例]   |
+--------------------------------------------------------------+
|                      主图区（K 线 + 缠论 overlay）             |
|   蜡烛图(红涨绿跌) + 笔/线段折线 + 笔中枢/线段中枢方框          |
|   + 买卖点 marker(带标签 1B/2B/L2B/3B)                        |
|   + 滚轮缩放 / 拖拽平移 / 十字光标 / 拖到最左增量加载           |
+--------------------------------------------------------------+
| 副图区 1：成交量（可折叠）                                     |
+--------------------------------------------------------------+
| 副图区 2：MACD（可折叠）                                       |
+--------------------------------------------------------------+
| 副图区 N：BOLL / RSI / KDJ（可折叠，最多 5 个）                 |
+--------------------------------------------------------------+
```

| # | 模块 | 字段 / 内容 |
|---|------|-------------|
| 1 | 顶栏工具栏 | 股票代码输入框、周期下拉（1 分钟/5 分钟/1 小时/日线）、副图指标菜单；**无搜索弹窗、无刷新按钮**（重载靠切换周期触发） |
| 2 | 图例 | 右上角图标，hover 显示颜色图例（笔=灰、线段=蓝、笔中枢=灰框、线段中枢=蓝框、买点=红、卖点=绿），非常驻图例栏 |
| 3 | 主图区 | K 线蜡烛图（红涨绿跌）+ 笔/线段折线 + 笔中枢/线段中枢方框 + 买卖点 marker 与类型标签；交互：滚轮缩放、拖拽平移、十字光标、拖到最左增量加载 |
| 4 | 副图指标区 | 成交量 / MACD / BOLL / RSI / KDJ（可折叠，≤5 个） |
| 5 | 状态态 | 加载中（骨架/loading）、无数据空态、后端错误提示 |

- **刷新语义**：本期不加显式刷新按钮；切换周期下拉触发 `watch(current{symbol,period})` 重载（见 D6）。后续若需强制重算再加。
- **图例折叠**：不占常驻高度，悬停/点击右上角图标展开，避免遮挡主图。

## Risks / Trade-offs

- **[KLineChart overlay figure 类型不确定]** 中枢矩形、带标签 marker 可能没有现成 figure → 探针阶段先验证，必要时用 `polygon`/组合 figure 兜底；这是探针存在的意义。
- **[数据源限频 / 在线依赖]** BaoStock 在线取数受限频 → 优先引导用 DuckDB 离线源（已具备）。
- **[复权历史价过期]** 复权走默认配置 → 若用 DuckDB 源，依赖其 `--full` 重刷机制；在线源每次拉取天然最新。
- **[买卖点标签映射不全]** `1p`（盘整背驰买点）等标签 UI 未最终定稿 → 阶段一先实现用户点名的买点标签，其余留待 UI 稿。
- **[稳定前缀续算依赖 chan.py 增量能力]** 复用已确认前缀、只重算尾部，需要计算服务能「从缓存前缀续算」；open-source 步进模式是否支持、是否需改计算逻辑待 spike 验证，若不可行则退化为「全量重算 + 仅缓存已确认前缀去重」。

## Migration Plan

本变更为纯新增，无回滚负担：

1. **Tier 0 探针**：`web/` 内最小 Vue + KLineChart 页面，硬编码一段序列化 JSON，验证笔/线段/中枢/买卖点 overlay 三类图形可渲染、缩放平移正常。
2. **后端**：`WebAPI/` 实现 `GET /api/klines?symbol=&period=` + 序列化（D2 契约）。
3. **联调**：前端 `setDataLoader`/`watch` 接后端，替换硬编码数据。
4. **周期切换 + 指标**：周期下拉 + 副图指标菜单。

回滚：删除 `WebAPI/`、`web/` 两个新增目录即可，计算路径零残留。

## Open Questions

- 线段级买卖点（`seg_bs_point_lst`）是否在阶段一展示？默认只展示笔级买卖点，线段级留作可选项。
- 买卖点标签完整缩写表（含卖点与 `1p` 盘背）最终以 UI 稿为准，阶段一先实现买点。
- 短周期（1 分钟）的历史深度与分页阈值（多少根 K 线触发增量加载）待数据量实测后定。
