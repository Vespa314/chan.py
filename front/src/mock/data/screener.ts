import type { Strategy, ScreenerResult } from '@/api/types'
import { stocks } from './stocks'

export const strategies: Strategy[] = [
  {
    id: 1,
    name: '日线一买选股',
    description: '扫描日线级别出现一买信号的股票，要求次级别底背离确认',
    bsp_types: ['1B'],
    kl_type: 'D',
    industries: ['银行', '白酒', '医药', '家电'],
    status: 'active',
    last_run: Date.now() - 3600000,
    result_count: 8,
  },
  {
    id: 2,
    name: '30分钟二三买共振',
    description: '30分钟级别二买和三买同时出现的股票，要求中枢突破放量',
    bsp_types: ['2B', '3B'],
    kl_type: '30m',
    industries: ['新能源', '电子', '半导体'],
    status: 'active',
    last_run: Date.now() - 7200000,
    result_count: 5,
  },
  {
    id: 3,
    name: '周线级别一卖预警',
    description: '周线出现一卖信号，顶分型确认，用于减仓预警',
    bsp_types: ['1S'],
    kl_type: 'W',
    industries: ['白酒', '食品饮料', '证券'],
    status: 'inactive',
    last_run: Date.now() - 86400000,
    result_count: 3,
  },
  {
    id: 4,
    name: '区间套买点扫描',
    description: '大级别买点 + 小级别买点共振，区间套策略',
    bsp_types: ['1B', '2B', 'L2B'],
    kl_type: '60m',
    industries: ['医药', '汽车', '电力'],
    status: 'active',
    last_run: Date.now() - 1800000,
    result_count: 12,
  },
]

let nextId = 5
export function addStrategy(s: Omit<Strategy, 'id'>): Strategy {
  const st = { ...s, id: nextId++ }
  strategies.push(st)
  return st
}
export function updateStrategy(id: number, patch: Partial<Strategy>) {
  const idx = strategies.findIndex((s) => s.id === id)
  if (idx >= 0) strategies[idx] = { ...strategies[idx], ...patch }
}
export function removeStrategy(id: number) {
  const idx = strategies.findIndex((s) => s.id === id)
  if (idx >= 0) strategies.splice(idx, 1)
}

/** 选股结果 */
export function getScreenerResults(strategyId: number): ScreenerResult[] {
  const r = (strategyId * 9301) % 233280 / 233280
  const count = 5 + Math.floor(r * 10)
  return Array.from({ length: count }, (_, i) => {
    const stock = stocks[(i + strategyId) % stocks.length]
    const rr = ((i + strategyId) * 49297) % 233280 / 233280
    return {
      code: stock.code,
      name: stock.name,
      industries: stock.industries,
      bsp_type: strategies.find((s) => s.id === strategyId)?.bsp_types[0] || '1B',
      price: stock.price,
      change_pct: +((rr - 0.5) * 6).toFixed(2),
      score: +(60 + rr * 40).toFixed(1),
    }
  })
}
