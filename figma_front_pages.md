# Figma 前端页面设计规格 — 其余页（Remaining Pages）

> 本文档是 `figma_front_core_pages.md` 的**续篇**，覆盖其余 6 页。全局设计规范（Design Tokens / 通用组件 / AppShell）见 **`figma_front_core_pages.md` Part 0**，本文档完全沿用，不再重复定义。

### 全局约定重申（沿用）

- **暗色专业终端**，A 股「红涨绿跌」：涨/阳线/买点/盈利正 = 红 `#F6465D`，跌/阴线/卖点/盈利负 = 绿 `#2EBD85`。
- 尺寸基准 **1440×900**，正文 14px，表格行高 44px，间距 4px 基准。
- chan-stock-manage 页面套 **AppShell 顶栏导航**（7 菜单 + 用户头像）；**登录页 `/login` 例外**，不套壳。
- 组件复用：数据表格 / 输入框 / 下拉 / 按钮 / 弹窗 / 抽屉 / 图表占位 / 标签 / 开关 / 汇总卡。

---

## Part 1 — 页面清单（其余 6 页）

| # | 页面 | 路由 | 来源 |
|---|------|------|------|
| 1 | 监控完成 | `/monitor/completed` | chan-stock-manage |
| 2 | 买卖点绩效 | `/performance` | chan-stock-manage |
| 3 | 条件选股 | `/screener` | chan-stock-manage |
| 4 | 预警提醒 | `/alerts` | chan-stock-manage |
| 5 | 登录 | `/login` | chan-stock-manage |
| 6 | 权限管理 | `/system` | chan-stock-manage |

---

## Part 2 — 页面 1：监控完成 `/monitor/completed`

**用途**：展示已结算卖出的监控股票，对盈利 < 5% 的标的做大模型亏损归因。

### 2.1 Frame 层级

```
AppShell.Content
└── CompletedPage (auto-layout vertical, gap 16)
    ├── ActionBar (auto-layout horizontal, gap 12)
    │   ├── LlmAnalyzeBtn（大模型分析，Button primary）
    │   └── ProgressHint（进行中状态，text/caption + 进度条）
    ├── CompletedTable（数据表格）
    │   └── 列：编码 / 名称 / 周期 / 买入价 / 卖出价 / 卖出时间 / 最终盈利% / 归因状态 / 操作(查看详情/重新分析)
    ├── FailureSummary (bg/surface, radius lg, padding lg)
    │   ├── 标题「失败原因汇总」
    │   └── 列表：编码 / 名称 / 失败原因分类 / 最终盈利% / 查看详情
    └── AttributionDialog（归因详情弹窗，点击「查看详情」打开）
```

### 2.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 操作工具条 | 「大模型分析」按钮（批量触发 `pnl_pct<5%`）、进度提示 | Button / 进度 |
| 完成列表表格 | 编码、名称、周期、买入价、卖出价、卖出时间、最终盈利%、归因状态、操作(查看详情/重新分析) | Table + Badge |
| 失败原因汇总区 | 编码、名称、失败原因分类、最终盈利%、查看详情 | 列表 |
| 归因详情弹窗 | 失败原因分类（缠论失效 / 计算逻辑错误）、证据、输入摘要、盈亏 | Dialog |

- 最终盈利% 用 `rise`/`fall` 着色。
- 归因状态 Badge：未归因（`text/disabled`）、归因中（`info`）、已归因（`accent`）。

### 2.3 状态态

- 归因进行中：按钮 loading + 进度提示。
- 无完成记录：空态「暂无已完成监控」。

---

## Part 3 — 页面 2：买卖点绩效 `/performance`

**用途**：按买卖点类型与周期统计历史胜率、盈亏比、样本数，下钻样本明细。

### 3.1 Frame 层级

```
AppShell.Content
└── PerformancePage (auto-layout vertical, gap 16)
    ├── FilterBar (auto-layout horizontal, gap 12)
    │   ├── PeriodSelect（周期）
    │   ├── TypeSelect（买卖点类型）
    │   └── DirSelect（方向）
    ├── PerformanceTable（数据表格）
    │   └── 列：周期 / 类型 / 方向 / 样本数 / 胜率% / 平均盈亏% / 盈亏比
    ├── WinRateChart (Chart Placeholder: bar「胜率对比」, height 220, 可选)
    └── SampleDrawer（右侧 Drawer，点某行下钻）
        └── 列：编码 / 名称 / 日期 / 盈亏%
```

### 3.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 筛选区 | 周期、买卖点类型、方向 | Select |
| 绩效统计表 | 周期、类型、方向、样本数、胜率%、平均盈亏%、盈亏比 | Table |
| 胜率对比图（可选） | 类型(x)、胜率%(y)，柱状图 | Chart Placeholder(bar) |
| 样本明细 Drawer | 编码、名称、日期、盈亏% | Drawer |

- 胜率% / 平均盈亏% 用 `rise`（>0）/ `fall`（<0）着色。

### 3.3 交互

- 点统计表某行 → 打开样本明细 Drawer。

---

## Part 4 — 页面 3：条件选股 `/screener`

**用途**：把周期/日期/买卖点类型/行业/指标阈值组合成可复用选股策略并执行扫描。

### 4.1 Frame 层级

```
AppShell.Content
└── ScreenerPage (auto-layout vertical, gap 16)
    ├── StrategyList (bg/surface, radius lg)
    │   ├── 头部：标题「选股策略」+「新建策略」按钮
    │   └── 列表：策略名 / 条件摘要 / 更新时间 / 操作(执行/编辑/删除)
    ├── ScanProgress（进行中状态 + 耗时，text/caption）
    ├── ResultTable（数据表格）
    │   └── 列：编码 / 名称 / 股价 / 行业(≤3) / 匹配指标 / 操作(加入自选)
    └── StrategyDialog（策略表单弹窗，新建/编辑打开）
```

### 4.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 策略列表 | 策略名、条件摘要、更新时间、操作(执行/编辑/删除)+ 新建策略 | 列表 + Button |
| 策略表单弹窗 | 策略名、周期、日期、买卖点类型、方向、行业、指标阈值 | Dialog + Form |
| 扫描进度 | 进行中状态、耗时 | 进度 |
| 扫描结果表 | 编码、名称、股价、行业(≤3)、匹配指标、操作(加入自选) | Table + Badge |

### 4.3 状态态

- 扫描中：结果区 loading + 进度提示。
- 删除策略：二次确认弹窗。

---

## Part 5 — 页面 4：预警提醒 `/alerts`

**用途**：管理预警规则（价格/买卖点/监控卖点）与查看站内通知。

### 5.1 Frame 层级

```
AppShell.Content
└── AlertsPage (auto-layout vertical, gap 16)
    ├── Tabs（「预警规则」/「站内通知」）
    ├── Tab1 预警规则
    │   ├── 头部：「新建规则」按钮
    │   └── RuleTable：类型(价格/买卖点/监控卖点) / 目标(股票/条件) / 阈值/参数 / 状态(开关) / 创建时间 / 操作(编辑/删除)
    ├── Tab2 站内通知
    │   ├── 头部：「全部已读」按钮
    │   └── NoticeList：时间 / 类型 / 内容 / 关联股票 / 已读状态 / 操作(标记已读)
    └── RuleDialog（规则表单弹窗）
```

### 5.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 子 tab | 预警规则 / 站内通知 | Tabs |
| 规则列表 | 类型(价格/买卖点/监控卖点)、目标(股票/条件)、阈值/参数、状态(开关)、创建时间、操作(编辑/删除)+ 新建规则 | Table + Switch |
| 规则表单弹窗 | 类型、目标股票、阈值/参数、启用状态 | Dialog + Form |
| 通知列表 | 时间、类型、内容、关联股票、已读状态、操作(标记已读)+ 全部已读 | 列表 |

- 未读通知高亮（`bg/surface-hover` + 加粗）；已读用 `text/secondary`。
- 规则状态用 Switch（on/off）。

---

## Part 6 — 页面 5：登录 `/login`

**用途**：用户认证入口。**不套 AppShell**，独立居中页面。

### 6.1 Frame 层级

```
Page (1440×900, fill: color/bg/base, 居中布局)
└── LoginCard (auto-layout vertical, width 400, padding 32, gap 20,
               bg/surface, radius lg, 水平垂直居中)
    ├── 标题「chan.py 缠论量化」
    ├── UsernameInput（用户名，Input，占位「用户名」）
    ├── PasswordInput（密码，Input type=password，占位「密码」）
    ├── LoginBtn（登录，Button primary，全宽）
    └── ErrorHint（登录失败提示，text/caption，color/rise）
```

### 6.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 登录卡片 | 标题、用户名、密码、登录按钮、失败提示 | Card + Input + Button |

### 6.3 状态态

- 登录失败：表单内错误提示（`color/rise`）。
- 提交中：登录按钮 loading。

---

## Part 7 — 页面 6：权限管理 `/system`

**用途**：admin 专属，管理用户、角色与角色-权限配置。

### 7.1 Frame 层级

```
AppShell.Content
└── SystemPage (auto-layout vertical, gap 16)
    ├── Tabs（「用户管理」/「角色管理」/「角色-权限配置」）
    ├── Tab1 用户管理
    │   ├── 头部：「新建用户」按钮
    │   └── UserTable：用户名 / 显示名 / 角色 / 状态(开关) / 创建时间 / 操作(编辑/重置密码/删除)
    ├── Tab2 角色管理
    │   ├── 头部：「新建角色」按钮
    │   └── RoleTable：角色名 / code / 是否 admin / 操作(编辑/删除)
    ├── Tab3 角色-权限配置
    │   ├── RoleSelect（选角色）
    │   ├── PermissionTree（勾选菜单权限 menu:* + 管理权限 manage）
    │   └── SaveBtn（保存）
    └── UserDialog / RoleDialog（表单弹窗）
```

### 7.2 模块与字段

| 模块 | 字段 / 内容 | 组件 |
|------|-------------|------|
| 子 tab | 用户管理 / 角色管理 / 角色-权限配置 | Tabs |
| 用户管理 | 用户名、显示名、角色、状态(开关)、创建时间、操作(编辑/重置密码/删除)+ 新建用户 | Table + Switch |
| 角色管理 | 角色名、code、是否 admin、操作(编辑/删除；admin 内置不可删改)+ 新建角色 | Table |
| 角色-权限配置 | 选角色 → 权限树（勾选 `menu:*` 7 项 + `manage`）→ 保存 | Select + Tree + Button |
| 表单弹窗 | 用户表单（用户名/显示名/角色/状态）、角色表单（角色名/code） | Dialog + Form |

- admin 角色行：`is_admin` Badge 标注，操作列「删除」置灰（不可删改）。

### 7.3 状态态

- 停用用户：Switch off，该用户无法登录。
- 删除角色（非 admin）：二次确认弹窗。

---

## 附：本文档约定说明

- 沿用 `figma_front_core_pages.md` Part 0 的全部 tokens 与组件；两文档合起来覆盖 10 页。
- 登录页为唯一不套 AppShell 的页面。
- 图表仍以占位 frame + 类型标注呈现。
