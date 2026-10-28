import { http, HttpResponse, delay } from 'msw'
import { monitorItems, completedItems, getProfitSeries } from '../data/monitor'

export const monitorHandlers = [
  http.get('/api/monitor', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    const keyword = url.searchParams.get('keyword') || ''
    let list = monitorItems
    if (keyword) list = list.filter((r) => r.code.includes(keyword) || r.name.includes(keyword))
    return HttpResponse.json(list)
  }),

  http.get('/api/monitor/completed', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    const keyword = url.searchParams.get('keyword') || ''
    let list = completedItems
    if (keyword) list = list.filter((r) => r.code.includes(keyword) || r.name.includes(keyword))
    return HttpResponse.json(list)
  }),

  http.get('/api/monitor/profit-series', async () => {
    await delay(200)
    return HttpResponse.json(getProfitSeries())
  }),

  http.post('/api/monitor/:id/end', async ({ params }) => {
    await delay(300)
    return HttpResponse.json({ success: true, id: Number(params.id) })
  }),

  http.post('/api/monitor/:id/analyze', async ({ params }) => {
    await delay(1500)
    const item = completedItems.find((c) => c.id === Number(params.id))
    if (item) item.ai_analyzed = true
    return HttpResponse.json({ success: true, id: Number(params.id) })
  }),
]
