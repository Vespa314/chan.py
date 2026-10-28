import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器 — 注入 token
client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截器 — 统一错误处理
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message || error.message || '请求失败'

    if (status === 401) {
      const auth = useAuthStore()
      auth.logout()
      ElMessage.error('登录已过期，请重新登录')
      // 延迟跳转避免在路由守卫中重复
      setTimeout(() => {
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }, 600)
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default client
