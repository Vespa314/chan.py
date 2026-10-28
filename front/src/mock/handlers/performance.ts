import { http, HttpResponse, delay } from 'msw'
import { performanceStats, performanceSamples } from '../data/performance'

export const performanceHandlers = [
  http.get('/api/performance/stats', async () => {
    await delay(300)
    return HttpResponse.json(performanceStats)
  }),

  http.get('/api/performance/samples', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    const bspType = url.searchParams.get('bsp_type') || ''
    let list = performanceSamples
    if (bspType) list = list.filter((s) => s.bsp_type === bspType)
    return HttpResponse.json(list)
  }),
]
