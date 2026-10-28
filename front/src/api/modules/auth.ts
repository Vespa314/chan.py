import client from '../client'
import type { UserInfo } from '@/stores/auth'

export interface LoginRes {
  token: string
  user: UserInfo
  perms: string[]
}

export interface MeRes {
  user: UserInfo
  perms: string[]
}

export function login(username: string, password: string) {
  return client.post<unknown, LoginRes>('/auth/login', { username, password })
}

export function me() {
  return client.post<unknown, MeRes>('/auth/me')
}

export function logout() {
  return client.post('/auth/logout')
}
