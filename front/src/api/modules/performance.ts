import client from '../client'
import type { PerformanceStat, PerformanceSample } from '@/api/types'

/** 买卖点绩效统计 */
export function getPerformanceStats() {
  return client.get<unknown, PerformanceStat[]>('/performance/stats')
}

/** 样本明细（bspType 可选筛选） */
export function getPerformanceSamples(bspType?: string) {
  return client.get<unknown, PerformanceSample[]>('/performance/samples', {
    params: { bsp_type: bspType },
  })
}
