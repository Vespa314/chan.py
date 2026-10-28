import { http, HttpResponse, delay } from 'msw'
import { users, roles, permissions, addUser, updateUser, removeUser, addRole, updateRole, removeRole } from '../data/system'

export const systemHandlers = [
  http.get('/api/system/users', async () => {
    await delay(200)
    return HttpResponse.json(users)
  }),

  http.post('/api/system/users', async ({ request }) => {
    await delay(200)
    const body = await request.json() as Parameters<typeof addUser>[0]
    return HttpResponse.json(addUser(body))
  }),

  http.put('/api/system/users/:id', async ({ params, request }) => {
    await delay(200)
    const body = await request.json() as Partial<Parameters<typeof updateUser>[1]>
    updateUser(Number(params.id), body)
    return HttpResponse.json({ success: true })
  }),

  http.delete('/api/system/users/:id', async ({ params }) => {
    await delay(200)
    const ok = removeUser(Number(params.id))
    if (!ok) return HttpResponse.json({ message: '管理员不可删除' }, { status: 400 })
    return HttpResponse.json({ success: true })
  }),

  http.post('/api/system/users/:id/reset-password', async ({ params }) => {
    await delay(200)
    return HttpResponse.json({ success: true, id: Number(params.id) })
  }),

  http.get('/api/system/roles', async () => {
    await delay(200)
    return HttpResponse.json(roles)
  }),

  http.post('/api/system/roles', async ({ request }) => {
    await delay(200)
    const body = await request.json() as Parameters<typeof addRole>[0]
    return HttpResponse.json(addRole(body))
  }),

  http.put('/api/system/roles/:id', async ({ params, request }) => {
    await delay(200)
    const body = await request.json() as Partial<Parameters<typeof updateRole>[1]>
    updateRole(Number(params.id), body)
    return HttpResponse.json({ success: true })
  }),

  http.delete('/api/system/roles/:id', async ({ params }) => {
    await delay(200)
    const ok = removeRole(Number(params.id))
    if (!ok) return HttpResponse.json({ message: '管理员角色不可删除' }, { status: 400 })
    return HttpResponse.json({ success: true })
  }),

  http.get('/api/system/permissions', async () => {
    await delay(100)
    return HttpResponse.json(permissions)
  }),
]
