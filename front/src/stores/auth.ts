import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/modules/auth'

export interface UserInfo {
  id: number
  username: string
  nickname: string
  role: string
  status: 'active' | 'disabled'
}

const TOKEN_KEY = 'chanpy_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<UserInfo | null>(null)
  const perms = ref<string[]>([])

  const isLogged = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /** 权限校验：admin 直接通过，否则检查 perms 数组 */
  function hasPerm(code: string): boolean {
    if (user.value?.role === 'admin') return true
    return perms.value.includes(code)
  }

  /** 菜单权限：menu:* 前缀匹配 */
  function hasMenu(key: string): boolean {
    return hasPerm(`menu:${key}`)
  }

  /** 登录 */
  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    token.value = res.token
    localStorage.setItem(TOKEN_KEY, res.token)
    user.value = res.user
    perms.value = res.perms
    return res
  }

  /** 拉取当前用户信息（token 已存在时） */
  async function fetchMe() {
    const res = await authApi.me()
    user.value = res.user
    perms.value = res.perms
    return res
  }

  /** 登出 */
  function logout() {
    token.value = ''
    user.value = null
    perms.value = []
    localStorage.removeItem(TOKEN_KEY)
  }

  return {
    token,
    user,
    perms,
    isLogged,
    isAdmin,
    hasPerm,
    hasMenu,
    login,
    fetchMe,
    logout,
  }
})
