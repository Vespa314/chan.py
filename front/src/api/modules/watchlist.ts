import client from '../client'
import type { Stock } from '@/api/types'

/** 自选文件夹 */
export interface WatchFolder {
  id: number
  name: string
  codes: string[]
}

/** 获取文件夹列表 */
export function getFolders() {
  return client.get<unknown, WatchFolder[]>('/watchlist/folders')
}

/** 新建文件夹 */
export function createFolder(name: string) {
  return client.post<unknown, WatchFolder>('/watchlist/folders', { name })
}

/** 删除文件夹 */
export function deleteFolder(id: number) {
  return client.delete<unknown, { success: boolean }>(`/watchlist/folders/${id}`)
}

/** 获取某文件夹下的股票（mock 返回全量数组；真实后端将服务端分页） */
export function getFolderStocks(folderId: number) {
  return client.get<unknown, Stock[]>(`/watchlist/folders/${folderId}/stocks`)
}

/** 添加股票到文件夹 */
export function addStock(folderId: number, code: string) {
  return client.post<unknown, { success: boolean }>(`/watchlist/folders/${folderId}/stocks`, {
    code,
  })
}

/** 从文件夹移出股票 */
export function removeStock(folderId: number, code: string) {
  return client.delete<unknown, { success: boolean }>(
    `/watchlist/folders/${folderId}/stocks/${code}`,
  )
}

/** 移动股票到其他文件夹 */
export function moveStock(from: number, to: number, code: string) {
  return client.post<unknown, { success: boolean }>('/watchlist/move', { from, to, code })
}
