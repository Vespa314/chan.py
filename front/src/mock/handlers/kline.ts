import { http, HttpResponse, delay } from 'msw'
import { getChanResult } from '../data/kline'

export const klineHandlers = [
  http.get('/api/kline/:code', async ({ params }) => {
    await delay(400)
    const code = params.code as string
    const result = getChanResult(code)
    return HttpResponse.json(result)
  }),
]
