import type { PerformanceStat, PerformanceSample } from '@/api/types'
import { stocks } from './stocks'

const bspTypes = ['1B', '2B', '3B', '1S', '2S', 'L2B', 'L2S', '3S']

function rand(i: number) {
  return ((i * 9301 + 49297) % 233280) / 233280
}

/** 7 行统计 */
export const performanceStats: PerformanceStat[] = bspTypes.slice(0, 7).map((t, i) => {
  const r = rand(i + 1)
  const samples = 20 + Math.floor(r * 80)
  const winRate = Math.floor(30 + r * 50)
  return {
    bsp_type: t,
    samples,
    win_rate: winRate,
    avg_pnl: +((winRate - 50) * 0.3 + (r - 0.5) * 2).toFixed(2),
    profit_ratio: +((winRate / 100) * (1 + r)).toFixed(2),
  }
})

/** 样本明细 40 条 */
export const performanceSamples: PerformanceSample[] = Array.from({ length: 40 }, (_, i) => {
  const stock = stocks[i % stocks.length]
  const r = rand(i + 1)
  const bspType = bspTypes[i % bspTypes.length]
  const direction = bspType.includes('B') ? 'buy' : 'sell'
  const bspPrice = +(stock.price * (0.85 + r * 0.2)).toFixed(2)
  const endPrice = +(bspPrice * (1 + (direction === 'buy' ? 1 : -1) * (0.05 + r * 0.2))).toFixed(2)
  const profit = +(((endPrice - bspPrice) / bspPrice) * 100).toFixed(2)
  return {
    id: i + 1,
    code: stock.code,
    name: stock.name,
    bsp_type: bspType,
    direction: direction as 'buy' | 'sell',
    bsp_price: bspPrice,
    end_price: endPrice,
    profit,
    bsp_date: Date.now() - Math.floor(r * 60 + 5) * 86400000,
    end_date: Date.now() - Math.floor(r * 5) * 86400000,
    hold_days: Math.floor(r * 30 + 2),
  }
})
