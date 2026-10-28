// ============================================================================
// chan.py 前端 API 类型定义
// ============================================================================

/** 通用分页响应 */
export interface PageRes<T> {
  list: T[]
  total: number
  page: number
  page_size: number
}

/** 分页查询参数 */
export interface PageQuery {
  page?: number
  page_size?: number
  keyword?: string
}

// ---------------------------------------------------------------------------
// 股票基础
// ---------------------------------------------------------------------------
export interface Stock {
  code: string
  name: string
  industries: string[]
  price: number
  change_pct: number
}

// ---------------------------------------------------------------------------
// K 线（design.md D2 序列化契约）
// ---------------------------------------------------------------------------
export interface KLine {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface BiPoint {
  t: number
  v: number
}

export interface Bi {
  begin: BiPoint
  end: BiPoint
  dir: 'UP' | 'DOWN'
  is_sure: boolean
}

export interface Seg extends Bi {
  level: number
}

export interface ZS {
  begin_t: number
  end_t: number
  low: number
  high: number
  mid: number
  level: 'bi' | 'seg'
}

export interface BspPoint {
  t: number
  v: number
  is_buy: boolean
  types: string[] // 原始枚举: '1','2','2s','3a','3b','1p'
}

export interface ChanResult {
  klines: KLine[]
  bi: Bi[]
  seg: Seg[]
  zs: ZS[]
  seg_zs: ZS[]
  bsp: BspPoint[]
}

// ---------------------------------------------------------------------------
// 买卖点记录
// ---------------------------------------------------------------------------
export interface BspRecord {
  id: number
  code: string
  name: string
  industries: string[]
  bsp_type: string // 1B/2B/3B/1S/2S/L2B/L2S/PZ-B/PZ-S
  direction: 'buy' | 'sell'
  bsp_price: number
  current_price: number
  bsp_date: number
  kl_type: string
  change_pct: number
}

export interface BspAggregate {
  industry: string
  total: number
  buy_count: number
  sell_count: number
}

// ---------------------------------------------------------------------------
// 监控
// ---------------------------------------------------------------------------
export interface MonitorItem {
  id: number
  code: string
  name: string
  industries: string[]
  bsp_type: string
  direction: 'buy' | 'sell'
  bsp_price: number
  current_price: number
  bsp_date: number
  kl_type: string
  change_pct: number
  max_profit: number
  max_drawdown: number
  status: 'monitoring' | 'completed'
}

export interface CompletedItem extends MonitorItem {
  end_date: number
  end_price: number
  profit: number
  attribution: string
  ai_analyzed: boolean
}

// ---------------------------------------------------------------------------
// 绩效
// ---------------------------------------------------------------------------
export interface PerformanceStat {
  bsp_type: string
  samples: number
  win_rate: number
  avg_pnl: number
  profit_ratio: number
}

export interface PerformanceSample {
  id: number
  code: string
  name: string
  bsp_type: string
  direction: 'buy' | 'sell'
  bsp_price: number
  end_price: number
  profit: number
  bsp_date: number
  end_date: number
  hold_days: number
}

// ---------------------------------------------------------------------------
// 选股
// ---------------------------------------------------------------------------
export interface Strategy {
  id: number
  name: string
  description: string
  bsp_types: string[]
  kl_type: string
  industries: string[]
  status: 'active' | 'inactive'
  last_run?: number
  result_count?: number
}

export interface ScreenerResult {
  code: string
  name: string
  industries: string[]
  bsp_type: string
  price: number
  change_pct: number
  score: number
}

// ---------------------------------------------------------------------------
// 预警
// ---------------------------------------------------------------------------
export interface AlertRule {
  id: number
  name: string
  code: string
  stock_name: string
  condition: string
  kl_type: string
  enabled: boolean
  trigger_count: number
  created_at: number
}

export interface AlertNotification {
  id: number
  rule_id: number
  rule_name: string
  code: string
  stock_name: string
  message: string
  triggered_at: number
  read: boolean
}

// ---------------------------------------------------------------------------
// 系统管理
// ---------------------------------------------------------------------------
export interface User {
  id: number
  username: string
  nickname: string
  role: string
  role_name: string
  status: 'active' | 'disabled'
  created_at: number
  last_login?: number
}

export interface Role {
  id: number
  name: string
  code: string
  description: string
  user_count: number
  perms: string[]
}

export interface Permission {
  id: number
  code: string
  name: string
  category: string
}
