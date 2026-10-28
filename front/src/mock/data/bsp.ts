import type { BspRecord, BspAggregate } from '@/api/types'
import { stocks } from './stocks'

const bspTypes = ['1B', '2B', '3B', '1S', '2S', 'L2B', 'L2S', 'PZ-B', 'PZ-S']
const klTypes = ['1m', '5m', '15m', '30m', '60m', 'D', 'W']

function rand(seed: number) {
  return ((seed * 9301 + 49297) % 233280) / 233280
}

/** 生成 60 条买卖点记录 */
export const bspRecords: BspRecord[] = Array.from({ length: 60 }, (_, i) => {
  const stock = stocks[i % stocks.length]
  const r = rand(i + 1)
  const bspType = bspTypes[i % bspTypes.length]
  const direction = bspType.includes('B') ? 'buy' : 'sell'
  const basePrice = stock.price
  return {
    id: i + 1,
    code: stock.code,
    name: stock.name,
    industries: stock.industries,
    bsp_type: bspType,
    direction: direction as 'buy' | 'sell',
    bsp_price: +(basePrice * (0.9 + r * 0.2)).toFixed(2),
    current_price: stock.price,
    bsp_date: Date.now() - Math.floor(r * 30) * 86400000,
    kl_type: klTypes[i % klTypes.length],
    change_pct: +((r - 0.5) * 10).toFixed(2),
  }
})

/** 板块聚合 */
export function getBspAggregate(): BspAggregate[] {
  const map = new Map<string, BspAggregate>()
  for (const r of bspRecords) {
    for (const ind of r.industries) {
      if (!map.has(ind)) {
        map.set(ind, { industry: ind, total: 0, buy_count: 0, sell_count: 0 })
      }
      const a = map.get(ind)!
      a.total++
      if (r.direction === 'buy') a.buy_count++
      else a.sell_count++
    }
  }
  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}
