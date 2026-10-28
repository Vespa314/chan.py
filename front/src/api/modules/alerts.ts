import client from '../client'
import type { AlertRule, AlertNotification } from '@/api/types'

/** 获取预警规则列表 */
export function getRules() {
  return client.get<unknown, AlertRule[]>('/alerts/rules')
}

/** 新建预警规则 */
export function createRule(data: Omit<AlertRule, 'id' | 'trigger_count' | 'created_at'>) {
  return client.post<unknown, AlertRule>('/alerts/rules', data)
}

/** 更新预警规则（含启停） */
export function updateRule(id: number, patch: Partial<AlertRule>) {
  return client.put<unknown, { success: boolean }>(`/alerts/rules/${id}`, patch)
}

/** 删除预警规则 */
export function deleteRule(id: number) {
  return client.delete<unknown, { success: boolean }>(`/alerts/rules/${id}`)
}

/** 获取站内通知列表 */
export function getNotifications() {
  return client.get<unknown, AlertNotification[]>('/alerts/notifications')
}

/** 标记单条通知已读 */
export function markRead(id: number) {
  return client.post<unknown, { success: boolean }>(`/alerts/notifications/${id}/read`)
}

/** 全部已读 */
export function markAllRead() {
  return client.post<unknown, { success: boolean }>('/alerts/notifications/read-all')
}
