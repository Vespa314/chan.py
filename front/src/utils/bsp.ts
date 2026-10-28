/**
 * 买卖点标签映射 — design.md D2
 * 前端做映射，不改后端枚举。
 * 原始枚举: '1','2','2s','3a','3b','1p'
 * 映射: 1B/1S, 2B/2S, L2B/L2S, 3B/3S, PZ-B/PZ-S
 */

const TYPE_MAP: Record<string, { buy: string; sell: string }> = {
  '1': { buy: '1B', sell: '1S' },
  '2': { buy: '2B', sell: '2S' },
  '2s': { buy: 'L2B', sell: 'L2S' },
  '3a': { buy: '3B', sell: '3S' },
  '3b': { buy: '3B', sell: '3S' },
  '1p': { buy: 'PZ-B', sell: 'PZ-S' },
}

/** 将原始 types 数组转为标签数组 */
export function bspLabels(types: string[], isBuy: boolean): string[] {
  return types.map((t) => {
    const m = TYPE_MAP[t]
    if (!m) return t
    return isBuy ? m.buy : m.sell
  })
}

/** 单个标签 */
export function bspLabel(type: string, isBuy: boolean): string {
  const m = TYPE_MAP[type]
  if (!m) return type
  return isBuy ? m.buy : m.sell
}

/** 所有买卖点类型标签（用于筛选下拉/图表轴） */
export const ALL_BSP_LABELS = ['1B', '2B', '3B', '1S', '2S', 'L2B', 'L2S', '3S', 'PZ-B', 'PZ-S']
