import { http, HttpResponse, delay } from 'msw'
import { strategies, getScreenerResults, addStrategy, updateStrategy, removeStrategy } from '../data/screener'

export const screenerHandlers = [
  http.get('/api/screener/strategies', async () => {
    await delay(200)
    return HttpResponse.json(strategies)
  }),

  http.post('/api/screener/strategies', async ({ request }) => {
    await delay(200)
    const body = await request.json() as Parameters<typeof addStrategy>[0]
    const s = addStrategy(body)
    return HttpResponse.json(s)
  }),

  http.put('/api/screener/strategies/:id', async ({ params, request }) => {
    await delay(200)
    const body = await request.json() as Partial<Parameters<typeof updateStrategy>[1]>
    updateStrategy(Number(params.id), body)
    return HttpResponse.json({ success: true })
  }),

  http.delete('/api/screener/strategies/:id', async ({ params }) => {
    await delay(200)
    removeStrategy(Number(params.id))
    return HttpResponse.json({ success: true })
  }),

  http.post('/api/screener/strategies/:id/run', async ({ params }) => {
    await delay(2000)
    const results = getScreenerResults(Number(params.id))
    return HttpResponse.json({ results, count: results.length })
  }),
]
