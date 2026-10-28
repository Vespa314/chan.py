import { http, HttpResponse, delay } from 'msw'
import { alertRules, alertNotifications, addRule, updateRule, removeRule, markRead, markAllRead } from '../data/alerts'

export const alertsHandlers = [
  http.get('/api/alerts/rules', async () => {
    await delay(200)
    return HttpResponse.json(alertRules)
  }),

  http.post('/api/alerts/rules', async ({ request }) => {
    await delay(200)
    const body = await request.json() as Parameters<typeof addRule>[0]
    return HttpResponse.json(addRule(body))
  }),

  http.put('/api/alerts/rules/:id', async ({ params, request }) => {
    await delay(200)
    const body = await request.json() as Partial<Parameters<typeof updateRule>[1]>
    updateRule(Number(params.id), body)
    return HttpResponse.json({ success: true })
  }),

  http.delete('/api/alerts/rules/:id', async ({ params }) => {
    await delay(200)
    removeRule(Number(params.id))
    return HttpResponse.json({ success: true })
  }),

  http.get('/api/alerts/notifications', async () => {
    await delay(200)
    return HttpResponse.json(alertNotifications)
  }),

  http.post('/api/alerts/notifications/:id/read', async ({ params }) => {
    await delay(100)
    markRead(Number(params.id))
    return HttpResponse.json({ success: true })
  }),

  http.post('/api/alerts/notifications/read-all', async () => {
    await delay(100)
    markAllRead()
    return HttpResponse.json({ success: true })
  }),
]
