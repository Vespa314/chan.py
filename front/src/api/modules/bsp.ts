import client from '../client'
import type { BspRecord, BspAggregate, PageRes } from '@/api/types'

/** 买卖点查询参数 */
export interface BspQuery {
  page: number
  page_size: number
  keyword?: string
  bsp_type?: string
  direction?: 'buy' | 'sell' | ''
  kl_type?: string
}

/** 买卖点列表（服务端分页） */
export function getBspList(query: BspQuery) {
  return client.get<unknown, PageRes<BspRecord>>('/bsp', { params: query })
}

/** 板块聚合 */
export function getBspAggregate() {
  return client.get<unknown, BspAggregate[]>('/bsp/aggregate')
}
