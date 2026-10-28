## Why

chan.py 已经能计算分型、笔、线段、笔中枢、线段中枢、买卖点，但结果只能通过 matplotlib 静态 PNG（`CPlotDriver`）或步进回放动画（`CAnimateDriver`）查看，无法像同花顺那样在浏览器里交互式地滚轮缩放、拖拽平移、切换周期与指标地浏览历史 K 线和缠论结构。需要一个 Web 前端，把 chan.py 已算好的缠论结构以交互式图表呈现，作为后续策略/交易系统的可视化基座。

## What Changes

- 新增后端 Web 服务（FastAPI）：提供 `GET /api/klines?symbol=&period=` 接口，返回 K 线 + 笔/线段/笔中枢/线段中枢/买卖点的 JSON；K 线来自 DuckDB 离线源，缠论结果经 `CChan` 现算，并将**稳定前缀**（未确认/虚元素之前的已确认部分）缓存到 PostgreSQL（键=股票+周期）。
- 新增 Web 前端（Vue3 + Vite + TypeScript + KLineChart）：主图 K 线（红涨绿跌，蜡烛/复权走默认配置）+ 缠论 overlay（灰色笔 / 蓝色线段 / 灰色框笔中枢 / 蓝色框线段中枢 / 买卖点 marker，买卖点买=红、卖=绿，标签 1B/2B/L2B/3B 等），副图指标（成交量/MACD/BOLL/RSI/KDJ，最多 5 个，可折叠）。
- 交互：滚轮缩放、拖拽平移、十字光标（KLineChart 默认行为）；拖到历史最左时经 `getBars('backward')` 向后端增量拉取更早 K 线。
- 周期切换：单级别切换（1 分钟/5 分钟/1 小时/日线等），切换即重算重绘。
- chan.py 的**计算逻辑不变**（`CBiList`/`CSegListChan`/`CZSList`/`CBSPointList` 均无感知）；仅在 `CChan` 上**新增序列化方法**（纯读取导出、不触碰计算）。

## Capabilities

### New Capabilities

- `chan-web-visualization`: Web 端交互式可视化缠论结构（K 线 + 笔/线段/笔中枢/线段中枢/买卖点）的能力。覆盖后端 JSON 序列化接口、前端图表渲染与缠论 overlay、缩放/平移/十字光标与历史增量加载、单级别周期切换与副图指标开关。

### Modified Capabilities

<!-- 无：不改动 kline-persistence 或任何既有计算行为。 -->

## Impact

- **新增文件**：后端服务（如 `App/web_api.py` 或独立 `WebAPI/` 目录）、前端工程（如 `web/` 目录：Vue3 + Vite + TS 项目）
- **复用**：`CChan` 计算流水线（计算逻辑不修改，仅新增序列化方法）、已完成变更 `persist-kl-to-duckdb` 提供的 DuckDB 离线源（`custom:DuckDBAPI.CDuckDB`）
- **依赖**：后端 `fastapi`/`uvicorn`、PostgreSQL 客户端驱动（复用 `persist-kl-to-duckdb` 已引入的 `psycopg2`/`sqlalchemy`）；前端 `klinecharts`、`vue`、`vite`（前端依赖独立于 `Script/requirements.txt`，以 `package.json` 管理）
- **调用方式**：启动 FastAPI 后浏览器打开前端，输入股票代码 + 选择周期查看；缠论计算路径零改动

## 范围边界（本期不做的）

- **搜索标的**（画布输入数字/字母触发弹窗搜索，需后端搜索接口 + 全市场股票池）—— 记入 backlog。
- **保存布局**（用户图表配置持久化到本地 PostgreSQL）—— 记入 backlog。注：PG 本身已因「缠论结果缓存」进入本期，但「保存布局」这一功能仍在 backlog。
- **画图工具**（趋势线/支撑阻力工具栏）—— 记入 backlog。
- **背驰标记 BI/XD/PZ/QS 的检测逻辑与可视化** —— 开源版 chan.py 未实现该判定，独立工作线，后续单独讨论。
- **图表设置面板**（样式/网格设置）—— 已删除该需求，走 KLineChart 默认样式。
