import client from '../client'
import type { ChanResult } from '../types'

/** 获取 K 线 + 缠论计算结果（design.md D2 序列化契约） */
export function getKLine(code: string) {
  return client.get<unknown, ChanResult>(`/kline/${code}`)
}
