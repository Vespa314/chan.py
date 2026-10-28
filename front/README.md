# chan.py 缠论量化前端工程

基于 Vue3 + Vite + TypeScript 的缠论技术分析量化终端前端，对标同花顺/富途/TradingView 暗色专业终端风格，A 股红涨绿跌语义。

## 技术栈

| 依赖 | 用途 |
|------|------|
| Vue 3.5 | 前端框架 |
| Vue Router 4 | 路由 |
| Pinia 2 | 状态管理 |
| Vite 5 | 构建 |
| TypeScript 5 | 类型 |
| Element Plus 2.8 | 表格/表单/弹窗/消息/分页/switch |
| ECharts 5 | 盈利走势折线 + 胜率柱状图 |
| KLineChart 9.8 | K 线图（红涨绿跌 + registerOverlay 自定义覆盖层） |
| Axios | HTTP 客户端 |
| MSW 2 | Mock Service Worker（Service Worker 层拦截网络请求） |
| @vueuse/core | useDebounceFn 等 |

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（http://localhost:5173）
npm run dev

# 构建生产包
npm run build

# 预览生产包
npm run preview
```

## 测试账号

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin | admin123 | 管理员 | 全权限（含系统管理） |
| trader | trader123 | 交易员 | 业务页面（无系统管理） |
| viewer | viewer123 | 观察者 | 仅 K 线/自选 |

## 功能页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 居中卡片 + 背景网格 |
| `/kline` | K 线分析 | KLineChart + 4 个缠论覆盖层（笔/线段/中枢/买卖点） |
| `/watchlist` | 自选 | 文件夹树 + 股票表格 + 搜索/批量操作 |
| `/bsp` | 买卖点 | 查询表单 + 结果/聚合 Tab + 区间套 Drawer |
| `/monitor` | 监控 | 监控中列表 + 手动结束 |
| `/monitor/completed` | 监控完成 | 盈利走势图 + 归因 + 大模型分析 |
| `/performance` | 绩效 | 胜率柱状图 + 统计表 + 下钻 |
| `/screener` | 选股 | 策略管理 + 执行扫描 + 结果 |
| `/alerts` | 预警 | 规则/通知 Tab + switch 启停 |
| `/system` | 权限管理 | 用户/角色/权限配置（admin 专属） |

## 缠论覆盖层

K 线页通过 KLineChart 的 `registerOverlay` API 实现 4 个自定义覆盖层：

| 覆盖层 | 颜色 | 说明 |
|--------|------|------|
| `chan_bi` | 灰 #9BA1A8 | 笔（分型连接的折线） |
| `chan_seg` | 蓝 #3B82F6 | 线段（笔的合成） |
| `chan_zs` | 灰框 | 中枢（价格重叠区间） |
| `chan_bsp` | 红买/绿卖 | 买卖点标签（1B/2B/3B/1S/2S 等） |

## Mock 数据

使用 MSW (Mock Service Worker) 在 Service Worker 层拦截 `/api/*` 请求，chrome-devtools Network 面板可见所有 mock 调用。切换真实后端只需关闭 MSW（设置 `.env` 中 `VITE_USE_MOCK=false`）。

## 设计系统

- 设计令牌：`src/styles/design.css`（原样复用 `uidesign/css/design.css`）
- Element Plus 暗色覆盖：`src/styles/element-overrides.css`
- 红涨绿跌：`--rise: #F6465D` / `--fall: #2EBD85`
- 字体：IBM Plex Sans (UI) + JetBrains Mono (数字/代码)

## 目录结构

```
front/
├── src/
│   ├── main.ts              # 入口（Vue + Pinia + Router + ElementPlus + MSW）
│   ├── App.vue              # 路由出口
│   ├── styles/              # 设计系统
│   ├── router/              # 路由 + 守卫
│   ├── stores/auth.ts       # 认证 + 权限
│   ├── directives/          # v-permission 指令
│   ├── api/                 # axios client + 类型 + 模块
│   ├── mock/                # MSW handlers + 数据
│   ├── components/
│   │   ├── layout/          # AppShell/Topnav/Sidebar
│   │   ├── ui/              # Panel/StatCard/SegControl 等薄封装
│   │   ├── charts/          # KLineChart/ProfitChart/WinRateChart
│   │   └── chan/            # 缠论覆盖层
│   ├── composables/         # usePagination/useTableSelection/useEcharts
│   ├── utils/               # bspLabel 买卖点标签映射
│   └── views/               # 11 个页面
├── uidesign/                # 原始静态设计稿（只读参考）
└── public/                  # mockServiceWorker.js
```

## RBAC 权限

- `menu:*` 权限控制菜单显隐
- `manage` 权限控制管理类按钮（新建/编辑/删除）
- `admin` 角色拥有所有权限
- `v-permission` 指令仅用于管理类按钮，业务按钮全部开放
