import { stocks, findStock } from './stocks'

export interface WatchFolder {
  id: number
  name: string
  codes: string[]
}

/** 自选文件夹 mock */
export const watchFolders: WatchFolder[] = [
  { id: 1, name: '默认自选', codes: ['sz.000001', 'sh.600519', 'sz.000858', 'sh.600036', 'sz.002594'] },
  { id: 2, name: '白酒板块', codes: ['sh.600519', 'sz.000858', 'sz.000568', 'sh.600809'] },
  { id: 3, name: '新能源', codes: ['sz.002594', 'sz.300750', 'sh.601012', 'sz.000625'] },
  { id: 4, name: '金融', codes: ['sz.000001', 'sh.600036', 'sh.601318', 'sh.601166', 'sh.600030'] },
  { id: 5, name: '医药', codes: ['sh.600276', 'sz.000538', 'sh.600436'] },
]

let nextFolderId = 6

export function addFolder(name: string): WatchFolder {
  const f = { id: nextFolderId++, name, codes: [] }
  watchFolders.push(f)
  return f
}

export function removeFolder(id: number) {
  const idx = watchFolders.findIndex((f) => f.id === id)
  if (idx >= 0) watchFolders.splice(idx, 1)
}

export function addStockToFolder(folderId: number, code: string) {
  const f = watchFolders.find((f) => f.id === folderId)
  if (f && !f.codes.includes(code)) f.codes.push(code)
}

export function removeStockFromFolder(folderId: number, code: string) {
  const f = watchFolders.find((f) => f.id === folderId)
  if (f) f.codes = f.codes.filter((c) => c !== code)
}

export function moveStock(fromId: number, toId: number, code: string) {
  removeStockFromFolder(fromId, code)
  addStockToFolder(toId, code)
}

/** 获取自选股票完整信息 */
export function getWatchStocks(folderId: number) {
  const f = watchFolders.find((f) => f.id === folderId)
  if (!f) return []
  return f.codes
    .map((c) => findStock(c))
    .filter(Boolean) as typeof stocks
}
