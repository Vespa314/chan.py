# Figma 前端页面设计规格 — 核心页（Core Pages）

> 本文档是 Figma AI 生成页面的**提示词 / 设计规格**。按「Design Tokens → 通用组件 → 逐页模块」三层组织，可直接作为 Figma AI（Make Design / use_figma）的输入。所有尺寸以 **1440×900 设计稿**为基准，采用 **auto-layout** 描述布局。

---

## Part 0 — 全局设计规范

### 0.1 视觉主题

- **暗色专业终端**风格，对标同花顺 / 富途 / TradingView 暗色。
- 金融语义遵循 **A 股「红涨绿跌」**：涨/阳线/买点/盈利为正 = 红，跌/阴线/卖点/盈利为负 = 绿。**与通用「红错绿对」相反**，全站金融数据一律以涨红跌绿为准；通用「成功/错误」不另设绿/红，避免与涨跌色冲突。

### 0.2 色彩系统（Color Styles）

| Token | 色值 | 用途 |
|-------|------|------|
| `color/bg/base` | `#0E1117` | 页面根背景 |
| `color/bg/surface` | `#161B22` | 卡片 / 面板 / 表头 |
| `color/bg/surface-hover` | `#1C2128` | 行 hover / 选中 |
| `color/bg/chart` | `#0A0D12` | 图表区背景（更深） |
| `color/border/base` | `#2A303A` | 常规边框 / 分隔线 |
| `color/border/strong` | `#3A424E` | 强调边框 |
| `color/text/primary` | `#E6E8EB` | 主文字 |
| `color/text/secondary` | `#9BA1A8` | 次要文字 / 表头 |
| `color/text/disabled` | `#565D66` | 占位 / 禁用 |
| `color/text/inverse` | `#0E1117` | 深色底上的反色文字（主按钮） |
| `color/accent/base` | `#3B82F6` | 主色 / 焦点 / 链接 |
| `color/accent/hover` | `#60A5FA` | 主色 hover |
| `color/rise` | `#F6465D` | **涨 / 阳线 / 买点 / 盈利为正** |
| `color/fall` | `#2EBD85` | **跌 / 阴线 / 卖点 / 盈利为负** |
| `color/warning` | `#F0B90B` | 告警 / 预警 |
| `color/info` | `#3B82F6` | 信息 |

### 0.3 字体（Text Styles）

- 字体族：中文 `PingFang SC` / `Noto Sans SC`；数字与代码 `Inter` 或等宽 `SF Mono` / `JetBrains Mono`。
- 层级：

| Token | 字号 / 字重 | 用途 |
|-------|-----------|------|
| `text/display` | 28 / Bold | 汇总大数字（总体盈利等） |
| `text/title` | 16 / Semibold | 页面 / 卡片 / 弹窗标题 |
| `text/body` | 14 / Regular | 表格正文、表单标签 |
| `text/caption` | 12 / Regular | 次要文字、图例、辅助 |
| `text/mono` | 14 / Regular（等宽） | 股价、编码、百分比数字 |

- 对齐规则：**数字右对齐**（等宽字体），**文本左对齐**。

### 0.4 间距与圆角（Spacing / Radius）

- 间距（4px 基准）：`xs=4` `sm=8` `md=12` `lg=16` `xl=20` `2xl=24` `3xl=32`。
- 圆角：`radius/sm=4` `radius/md=6` `radius/lg=8` `radius/full=999`。

### 0.5 通用组件（Components）

> 以下组件以 Figma Component + Variant 形式建立，页面内复用，不重复定义。

| 组件 | Variant / 属性 | 关键规范 |
|------|---------------|---------|
| **数据表格 Table** | 带选择列 / 不带选择列 | 表头 40px 高、`bg/surface`、文字 `text/secondary` 12px、底边 `border/base`；数据行 44px 高、hover `bg/surface-hover`、行间 1px 分隔；单元格水平 padding 12px；数字列右对齐等宽 |
| **输入框 Input** | normal / focus / disabled | 高 32px，`bg/surface`，1px `border/base`，radius `md`；focus 边框 `accent/base`；placeholder `text/disabled` |
| **下拉选择 Select** | normal / open | 同 Input，右侧 chevron 图标；展开菜单 `bg/surface`，选项 hover `bg/surface-hover` |
| **按钮 Button** | primary / default / danger / disabled | 高 32px，radius `md`，水平 padding 16px；primary=`accent/base` 填充白字；default=`bg/surface`+边框；danger=`rise` 填充；disabled=`text/disabled` 50% 透明 |
| **弹窗 Dialog** | — | 居中，宽 480px，标题 + 内容 + 底部按钮；遮罩 `rgba(0,0,0,0.5)` |
| **抽屉 Drawer** | — | 右侧滑出，宽 560px，标题 + 内容 + 底部按钮；遮罩同 Dialog |
| **图表占位 Chart Placeholder** | kline / line / bar | `bg/chart` 填充，中央水印标注图表类型；用极简几何示意，标注「示意」 |
| **标签 Badge** | default / rise / fall / warning | 胶囊 radius `full`，12px 文字；涨用 `rise`、跌用 `fall` |
| **开关 Switch** | on / off | 用于启用停用、已读等 |
| **汇总卡 Stat Card** | — | `bg/surface`、radius `lg`、padding `lg`；大数字 `text/display` + 标签 `text/caption` |

### 0.6 应用外壳（App Shell）— 仅 chan-stock-manage 页面

chan-stock-manage 的页面共享一个**顶部导航外壳**；chan-web-viewer 的 K 线图页为**独立单页**，不套此壳。

```
AppShell (1440×900, vertical auto-layout)
├── TopNav (auto-layout horizontal, height 52, padding 16, gap 24)
│   ├── Logo/标题
│   ├── 菜单项 × 7（自选 / 买卖点 / 监控 / 绩效 / 选股 / 预警 / 权限管理）
│   │     └── 选中态：accent 下划线或高亮；权限管理仅 admin 可见
│   └── 用户头像 + 用户名（右侧，点击出登出菜单）
└── Content (auto-layout vertical, padding 24, gap 16, flex:1)
    └── 各页面内容
```

- 菜单可见性由 RBAC 控制（无 `menu:*` 权限的菜单隐藏）。

---

## Part 1 — 页面清单（核心 4 页）

| # | 页面 | 路由 | 来源 |
|---|------|------|------|
| 1 | K 线图表页 | 独立单页 | chan-web-viewer |
| 2 | 我的自选 | `/watchlist` | chan-stock-manage |
| 3 | 历史买卖点 | `/bsp` | chan-stock-manage |
| 4 | 股票监控 | `/monitor` | chan-stock-manage |

---

## Part 2 — 页面 1：K 线图表页

**用途**：交互式浏览单只股票指定周期的 K 线与缠论结构（笔/线段/笔中枢/线段中枢/买卖点）。
**来源**：chan-web-viewer（独立单页，不套 AppShell）。

### 2.1 Frame 层级

```
Page (1440×900, fill: color/bg/base)
├── TopBar (auto-layout horizontal, height 48, padding 16, gap 12, align center)
│   ├── SymbolInput  (Input，宽 200，占位「输入股票代码，如 sz.000001」)
│   ├── PeriodSelect  (Select，周期：1分钟/5分钟/1小时/日线)
│   ├── IndicatorMenu (Select 多选，副图指标：成交量/MACD/BOLL/RSI/KDJ)
│   └── LegendIcon    (右上角图标，hover 出 tooltip)
├── MainChart  (Chart Placeholder: kline, flex:1, fill: color/bg/chart)
│     └── 内含：蜡烛图 + 笔/线段折线 + 笔中枢/线段中枢方框 + 买卖点 marker（示意）
├── SubChart 1 (Chart Placeholder: line「成交量」, height 120, collapsible)
├── SubChart 2 (Chart Placeholder: line「MACD」, height 120, collapsible)
└── SubChart N (BOLL/RSI/KDJ，同类，最多 5 个副图)
```

### 2.2 模块与字段

| 模块 | 字段 / 内容 | 组件 | 布局 |
|------|-------------|------|------|
| 顶栏工具栏 | 股票代码输入框、周期下拉、副图指标菜单、图例图标 | Input / Select / Icon | horizontal，gap 12 |
| 主图区 | K 线蜡烛图 + 笔(灰线) + 线段(蓝线) + 笔中枢(灰框) + 线段中枢(蓝框) + 买卖点 marker(买红/卖绿，标签 1B/2B/L2B/3B) | Chart Placeholder(kline) | flex:1 |
| 副图指标区 | 成交量 / MACD / BOLL / RSI / KDJ | Chart Placeholder(line) | 纵向堆叠，每块高 120，可折叠 |
| 图例 tooltip | 笔=灰、线段=蓝、笔中枢=灰框、线段中枢=蓝框、买点=红、卖点=绿 | Tooltip | 悬停于右上图标显示 |

### 2.3 缠论样式约定（主图 overlay）

| 元素 | 颜色 | 形态 |
|------|------|------|
| 笔 | 灰 `#9BA1A8` | 两点折线 |
| 线段 | 蓝 `#3B82F6` | 两点折线（比笔粗） |
| 笔中枢 | 灰 `#9BA1A8` | 半透明方框 |
| 线段中枢 | 蓝 `#3B82F6` | 半透明方框 |
| 买点 marker | `color/rise`（红） | 标记 + 标签 `1B`/`2B`/`L2B`/`3B` |
| 卖点 marker | `color/fall`（绿） | 标记 + 标签 `1S`/`2S`/`L2S`/`3S` |

> 买卖点标签完整映射：`T1→1B/1S`、`T2→2B/2S`、`T2S→L2B/L2S`、`T3A/T3B→3B/3S`、`T1P→PZ-B/PZ-S`（阶段一先实现买点 1B/2B/L2B/3B）。

### 2.4 交互与状态

- 交互：滚轮缩放、拖拽平移、十字光标、拖到最左增量加载（图上行为，不在静态稿体现）。
- 状态态：加载中（主图骨架屏）、无数据空态（居中「暂无数据」+ 引导输入代码）、错误态（居中错误提示 + 重试）。

---

## Part 3 — 页面 2：我的自选 `/watchlist`

**用途**：文件夹分类管理自选股票，查看名称/编码/股价/行业。

### 3.1 Frame 层级

```
AppShell.Content
└── WatchlistPage (auto-layout horizontal, gap 16, flex:1)
    ├── FolderPanel (width 220, auto-layout vertical, bg/surface, radius lg)
    │   ├── 头部：标题「自选」+ 新建文件夹按钮
    │   └── FolderTree（列表：文件夹名 + 股票数；顶部「全部」虚拟节点）
    └── MainPanel (auto-layout vertical, gap 12, flex:1)
        ├── Toolbar (auto-layout horizontal, gap 12)
        │   ├── SearchInput（搜索名称/编码）
        │   ├── AddBtn（添加股票）
        │   └── BatchRemoveBtn（批量移出）
        └── StockTable（数据表格，带选择列）
```

### 3.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 文件夹树（左） | 文件夹名、股票数；操作：新建/重命名/删除/切换 | 树列表 |
| 工具条 | 搜索框、添加股票、批量移出 | Input / Button |
| 股票表格 | 选择框、编码、名称、股价、涨跌幅、行业(≤3)、操作(移出/移动到文件夹) | Table + Badge |
| 加入自选弹窗 | 文件夹名（默认 = 日期，可改） | Dialog |

- 股价数字用 `text/mono` 右对齐；涨跌幅用 `rise`/`fall` 着色；行业用 `Badge`（最多 3 个）。

### 3.3 状态态

- 某文件夹无股票：空态「暂无自选股票」+ 引导从买卖点页加入。
- 删除含股文件夹：二次确认弹窗。

---

## Part 4 — 页面 3：历史买卖点 `/bsp`

**用途**：按周期/日期/类型查询全市场出现买卖点的股票，板块聚合，批量加入自选 / 监控。

### 4.1 Frame 层级

```
AppShell.Content
└── BspPage (auto-layout vertical, gap 16)
    ├── QueryBar (auto-layout horizontal, gap 12)
    │   ├── PeriodSelect（周期）
    │   ├── DatePicker（日期）
    │   ├── TypeSelect（买卖点类型）
    │   ├── DirSelect（方向：买/卖）
    │   ├── QueryBtn（查询）
    │   └── ResetBtn（重置）
    ├── ActionBar (auto-layout horizontal, gap 12)
    │   ├── AddToWatchlistBtn（批量加入自选）
    │   └── AddToMonitorBtn（加入监控）
    ├── ResultTable（数据表格，带选择列）
    │   └── 列：选择框 / 编码 / 名称 / 股价 / 行业(≤3) / 买卖点类型 / 方向 / 买卖点价格 / 买卖点日期 / 周期 / 操作(区间套)
    ├── SectorAggregate (Tab 切换「结果列表 / 板块聚合」)
    │   └── 板块聚合表：行业 / 买点股票数 / 卖点股票数 / 合计
    └── NestingDrawer（右侧 Drawer，点某行「区间套」展开）
        └── 周期(日/60M/30M) + 各周期买卖点列表
```

### 4.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 查询筛选区 | 周期、日期、买卖点类型、方向、查询/重置 | Select / DatePicker / Button |
| 操作工具条 | 批量加入自选、加入监控（基于多选） | Button |
| 结果表 | 选择框、编码、名称、股价、行业(≤3)、买卖点类型、方向、买卖点价格、买卖点日期、周期、操作 | Table + Badge |
| 板块聚合区 | 行业、买点股票数、卖点股票数、合计（点行业回填筛选） | Table |
| 区间套 Drawer | 周期(日/60M/30M)、买卖点列表(类型/方向/价格/日期) | Drawer |

- 买卖点方向用 Badge：买=`rise`、卖=`fall`。

### 4.3 弹窗

- **加入自选弹窗**：文件夹名输入（默认 = 查询日期，可改）→ 确认。
- **加入监控弹窗**：周期（默认 = 查询周期）、监控时间可设 → 确认。

### 4.4 状态态

- 查询中：结果表 loading。
- 无结果：空态「未查询到买卖点」。

---

## Part 5 — 页面 4：股票监控 `/monitor`

**用途**：监控列表、每只盈利走势折线、总体盈利。

### 5.1 Frame 层级

```
AppShell.Content
└── MonitorPage (auto-layout vertical, gap 16)
    ├── StatCards (auto-layout horizontal, gap 16)
    │   ├── StatCard：总体盈利(%)  ← text/display
    │   └── StatCard：监控中数量
    ├── ProfitChart (Chart Placeholder: line「盈利走势」, height 280)
    │   └── 顶部切换：「汇总 / 单只」（Select）
    ├── FilterBar（搜索框）
    └── MonitorTable（数据表格）
        └── 列：编码 / 名称 / 周期 / 监控起始时间 / 买入价 / 现价 / 盈利% / 状态 / 操作(手动结束)
```

### 5.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 汇总卡 | 总体盈利(%)、监控中数量 | Stat Card |
| 盈利走势折线图 | 时间轴、盈利%(时序)；切换汇总/单只 | Chart Placeholder(line) |
| 监控列表表格 | 编码、名称、周期、监控起始时间、买入价、现价、盈利%、状态、操作(手动结束) | Table + Badge |
| 筛选 | 搜索框 | Input |

- 盈利% 用 `rise`（正）/ `fall`（负）着色，`text/mono`。
- 状态 Badge：`monitoring`（监控中）。

### 5.3 状态态

- 无监控中股票：空态「暂无监控股票」。
- 后端自动结算后该行转「监控完成」页（本页行消失）。

---

## 附：本文档约定说明

- 所有页面为**暗色主题**，遵循 A 股「红涨绿跌」。
- 图表以**占位 frame + 类型标注**呈现，不细化真实数据点。
- 尺寸基于 **1440×900**，正文 14px、表格行高 44px、间距 4px 基准。
- 组件在 Part 0.5 定义一次，各页面引用组件名即可。
