import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 公开路由直接放行
  if (to.meta.public) {
    // 已登录用户访问登录页 → 跳首页
    if (to.name === 'login' && auth.token) {
      return { path: '/kline' }
    }
    return true
  }

  // 未登录 → 跳登录
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // token 存在但 user 未加载 → 拉取用户信息
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  // 权限校验
  const perm = to.meta.perm as string | undefined
  if (perm && !auth.hasPerm(perm)) {
    return { path: '/403' }
  }

  return true
})

export default router
