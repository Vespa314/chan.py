import { http, HttpResponse, delay } from 'msw'
import { bspRecords, getBspAggregate } from '../data/bsp'

export const bspHandlers = [
  http.get('/api/bsp', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    const page = Number(url.searchParams.get('page') || '1')
    const pageSize = Number(url.searchParams.get('page_size') || '20')
    const keyword = url.searchParams.get('keyword') || ''
    const bspType = url.searchParams.get('bsp_type') || ''
    const direction = url.searchParams.get('direction') || ''

    let list = bspRecords
    if (keyword) list = list.filter((r) => r.code.includes(keyword) || r.name.includes(keyword))
    if (bspType) list = list.filter((r) => r.bsp_type === bspType)
    if (direction) list = list.filter((r) => r.direction === direction)

    const total = list.length
    const start = (page - 1) * pageSize
    const pageList = list.slice(start, start + pageSize)
    return HttpResponse.json({ list: pageList, total, page, page_size: pageSize })
  }),

  http.get('/api/bsp/aggregate', async () => {
    await delay(200)
    return HttpResponse.json(getBspAggregate())
  }),
]
