import { http, HttpResponse, delay } from 'msw'
import { watchFolders, addFolder, removeFolder, addStockToFolder, removeStockFromFolder, moveStock, getWatchStocks } from '../data/watchlist'

export const watchlistHandlers = [
  http.get('/api/watchlist/folders', async () => {
    await delay(200)
    return HttpResponse.json(watchFolders)
  }),

  http.post('/api/watchlist/folders', async ({ request }) => {
    await delay(200)
    const body = await request.json() as { name: string }
    const f = addFolder(body.name)
    return HttpResponse.json(f)
  }),

  http.delete('/api/watchlist/folders/:id', async ({ params }) => {
    await delay(200)
    removeFolder(Number(params.id))
    return HttpResponse.json({ success: true })
  }),

  http.get('/api/watchlist/folders/:id/stocks', async ({ params }) => {
    await delay(200)
    return HttpResponse.json(getWatchStocks(Number(params.id)))
  }),

  http.post('/api/watchlist/folders/:id/stocks', async ({ params, request }) => {
    await delay(200)
    const body = await request.json() as { code: string }
    addStockToFolder(Number(params.id), body.code)
    return HttpResponse.json({ success: true })
  }),

  http.delete('/api/watchlist/folders/:id/stocks/:code', async ({ params }) => {
    await delay(200)
    removeStockFromFolder(Number(params.id), params.code as string)
    return HttpResponse.json({ success: true })
  }),

  http.post('/api/watchlist/move', async ({ request }) => {
    await delay(200)
    const body = await request.json() as { from: number; to: number; code: string }
    moveStock(body.from, body.to, body.code)
    return HttpResponse.json({ success: true })
  }),
]
