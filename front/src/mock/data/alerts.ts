import type { AlertRule, AlertNotification } from '@/api/types'
import { stocks } from './stocks'

export const alertRules: AlertRule[] = [
  {
    id: 1, name: '平安银行一买提醒', code: 'sz.000001', stock_name: '平安银行',
    condition: '出现1B买点', kl_type: 'D', enabled: true, trigger_count: 3,
    created_at: Date.now() - 86400000 * 7,
  },
  {
    id: 2, name: '贵州茅台顶分型', code: 'sh.600519', stock_name: '贵州茅台',
    condition: '顶分型确认', kl_type: '60m', enabled: true, trigger_count: 1,
    created_at: Date.now() - 86400000 * 3,
  },
  {
    id: 3, name: '比亚迪突破中枢', code: 'sz.002594', stock_name: '比亚迪',
    condition: '价格突破中枢上沿', kl_type: '30m', enabled: false, trigger_count: 5,
    created_at: Date.now() - 86400000 * 14,
  },
  {
    id: 4, name: '宁德时代底背离', code: 'sz.300750', stock_name: '宁德时代',
    condition: 'MACD底背离', kl_type: 'D', enabled: true, trigger_count: 2,
    created_at: Date.now() - 86400000 * 5,
  },
]

export const alertNotifications: AlertNotification[] = [
  {
    id: 1, rule_id: 1, rule_name: '平安银行一买提醒', code: 'sz.000001', stock_name: '平安银行',
    message: '平安银行日线出现一买信号，当前价格 11.85', triggered_at: Date.now() - 3600000, read: false,
  },
  {
    id: 2, rule_id: 2, rule_name: '贵州茅台顶分型', code: 'sh.600519', stock_name: '贵州茅台',
    message: '贵州茅台60分钟顶分型确认，注意减仓', triggered_at: Date.now() - 7200000, read: false,
  },
  {
    id: 3, rule_id: 4, rule_name: '宁德时代底背离', code: 'sz.300750', stock_name: '宁德时代',
    message: '宁德时代日线MACD底背离，关注买点', triggered_at: Date.now() - 86400000, read: true,
  },
  {
    id: 4, rule_id: 1, rule_name: '平安银行一买提醒', code: 'sz.000001', stock_name: '平安银行',
    message: '平安银行日线一买信号触发（历史）', triggered_at: Date.now() - 86400000 * 2, read: true,
  },
]

let nextRuleId = 5
let nextNotiId = 5

export function addRule(r: Omit<AlertRule, 'id' | 'trigger_count' | 'created_at'>): AlertRule {
  const rule = { ...r, id: nextRuleId++, trigger_count: 0, created_at: Date.now() }
  alertRules.push(rule)
  return rule
}
export function updateRule(id: number, patch: Partial<AlertRule>) {
  const idx = alertRules.findIndex((r) => r.id === id)
  if (idx >= 0) alertRules[idx] = { ...alertRules[idx], ...patch }
}
export function removeRule(id: number) {
  const idx = alertRules.findIndex((r) => r.id === id)
  if (idx >= 0) alertRules.splice(idx, 1)
}
export function markRead(id: number) {
  const n = alertNotifications.find((n) => n.id === id)
  if (n) n.read = true
}
export function markAllRead() {
  alertNotifications.forEach((n) => (n.read = true))
}
