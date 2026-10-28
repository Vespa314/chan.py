import client from '../client'
import type { Strategy, ScreenerResult } from '@/api/types'

/** 策略列表 */
export function getStrategies() {
  return client.get<unknown, Strategy[]>('/screener/strategies')
}

/** 新建策略 */
export function createStrategy(data: Omit<Strategy, 'id'>) {
  return client.post<unknown, Strategy>('/screener/strategies', data)
}

/** 更新策略 */
export function updateStrategy(id: number, patch: Partial<Strategy>) {
  return client.put<unknown, { success: boolean }>(`/screener/strategies/${id}`, patch)
}

/** 删除策略 */
export function deleteStrategy(id: number) {
  return client.delete<unknown, { success: boolean }>(`/screener/strategies/${id}`)
}

/** 执行策略 */
export function runStrategy(id: number) {
  return client.post<unknown, { results: ScreenerResult[]; count: number }>(
    `/screener/strategies/${id}/run`,
  )
}
