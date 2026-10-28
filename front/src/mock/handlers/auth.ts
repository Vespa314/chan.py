import { http, HttpResponse, delay } from 'msw'
import { findUser, mockUsers } from '../data/auth'

export const authHandlers = [
  http.post('/api/auth/login', async ({ request }) => {
    await delay(300)
    const body = await request.json() as { username: string; password: string }
    const user = findUser(body.username)
    if (!user || user.password !== body.password) {
      return HttpResponse.json({ message: '用户名或密码错误' }, { status: 401 })
    }
    if (user.status === 'disabled') {
      return HttpResponse.json({ message: '账号已禁用' }, { status: 403 })
    }
    return HttpResponse.json({
      token: `mock-token-${user.id}-${Date.now()}`,
      user: { id: user.id, username: user.username, nickname: user.nickname, role: user.role, status: user.status },
      perms: user.perms,
    })
  }),

  http.post('/api/auth/me', async ({ request }) => {
    await delay(150)
    // 从 token 解析用户身份：mock-token-{id}-{timestamp}
    const auth = request.headers.get('Authorization') || ''
    const token = auth.replace('Bearer ', '')
    const match = token.match(/^mock-token-(\d+)-/)
    const userId = match ? Number(match[1]) : 1
    const user = mockUsers.find((u) => u.id === userId) || mockUsers[0]
    return HttpResponse.json({
      user: { id: user.id, username: user.username, nickname: user.nickname, role: user.role, status: user.status },
      perms: user.perms,
    })
  }),

  http.post('/api/auth/logout', async () => {
    return HttpResponse.json({ success: true })
  }),
]
