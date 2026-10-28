import type { MonitorItem, CompletedItem } from '@/api/types'
import { stocks } from './stocks'

const bspTypes = ['1B', '2B', '3B', '1S', '2S', 'L2B']
const klTypes = ['15m', '30m', '60m', 'D']
const attributions = [
  '本级别出现一买信号，次级别底背离确认，区间套共振明显，建议持有。',
  '二买点形成后价格突破中枢上沿，量能配合良好，趋势确立。',
  '三买点后出现回调，但未跌回中枢，属强势调整，继续持有。',
  '一卖信号触发，顶分型确认，建议减仓观望。',
  '中枢扩展后选择向上突破，线段级别买点成立。',
  '小级别背驰引发大级别转折，区间套买点有效。',
]

function rand(i: number) {
  return ((i * 9301 + 49297) % 233280) / 233280
}

/** 监控中 6 条 */
export const monitorItems: MonitorItem[] = Array.from({ length: 6 }, (_, i) => {
  const stock = stocks[i + 3]
  const r = rand(i + 1)
  const bspType = bspTypes[i % bspTypes.length]
  const direction = bspType.includes('B') ? 'buy' : 'sell'
  const bspPrice = +(stock.price * (0.9 + r * 0.15)).toFixed(2)
  return {
    id: i + 1,
    code: stock.code,
    name: stock.name,
    industries: stock.industries,
    bsp_type: bspType,
    direction: direction as 'buy' | 'sell',
    bsp_price: bspPrice,
    current_price: stock.price,
    bsp_date: Date.now() - Math.floor(r * 20) * 86400000,
    kl_type: klTypes[i % klTypes.length],
    change_pct: +((r - 0.5) * 8).toFixed(2),
    max_profit: +((stock.price - bspPrice) / bspPrice * 100).toFixed(2),
    max_drawdown: +(r * -5).toFixed(2),
    status: 'monitoring',
  }
})

/** 完成 6 条 */
export const completedItems: CompletedItem[] = Array.from({ length: 6 }, (_, i) => {
  const stock = stocks[i + 10]
  const r = rand(i + 100)
  const bspType = bspTypes[(i + 2) % bspTypes.length]
  const direction = bspType.includes('B') ? 'buy' : 'sell'
  const bspPrice = +(stock.price * (0.85 + r * 0.2)).toFixed(2)
  const endPrice = +(bspPrice * (1 + (direction === 'buy' ? 1 : -1) * (0.05 + r * 0.15))).toFixed(2)
  const profit = +(((endPrice - bspPrice) / bspPrice) * 100).toFixed(2)
  return {
    id: i + 100,
    code: stock.code,
    name: stock.name,
    industries: stock.industries,
    bsp_type: bspType,
    direction: direction as 'buy' | 'sell',
    bsp_price: bspPrice,
    current_price: stock.price,
    bsp_date: Date.now() - Math.floor(r * 40 + 10) * 86400000,
    kl_type: klTypes[i % klTypes.length],
    change_pct: +((r - 0.5) * 6).toFixed(2),
    max_profit: +(Math.abs(profit) + r * 3).toFixed(2),
    max_drawdown: +(r * -4).toFixed(2),
    status: 'completed',
    end_date: Date.now() - Math.floor(r * 5) * 86400000,
    end_price: endPrice,
    profit,
    attribution: attributions[i % attributions.length],
    ai_analyzed: i % 2 === 0,
  }
})

/** 14 日盈利时序 */
export function getProfitSeries(): { date: string; value: number }[] {
  const series: { date: string; value: number }[] = []
  let v = 0
  for (let i = 13; i >= 0; i--) {
    const r = rand(i + 200)
    v += (r - 0.45) * 3
    const d = new Date(Date.now() - i * 86400000)
    series.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      value: +v.toFixed(2),
    })
  }
  return series
}
