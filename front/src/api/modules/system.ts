import client from '../client'
import type { User, Role, Permission } from '@/api/types'

// --- 用户 ---
export function getUsers() {
  return client.get<unknown, User[]>('/system/users')
}

export function createUser(data: Omit<User, 'id' | 'created_at'>) {
  return client.post<unknown, User>('/system/users', data)
}

export function updateUser(id: number, patch: Partial<User>) {
  return client.put<unknown, { success: boolean }>(`/system/users/${id}`, patch)
}

export function deleteUser(id: number) {
  return client.delete<unknown, { success: boolean }>(`/system/users/${id}`)
}

export function resetPassword(id: number) {
  return client.post<unknown, { success: boolean; id: number }>(`/system/users/${id}/reset-password`)
}

// --- 角色 ---
export function getRoles() {
  return client.get<unknown, Role[]>('/system/roles')
}

export function createRole(data: Omit<Role, 'id' | 'user_count'>) {
  return client.post<unknown, Role>('/system/roles', data)
}

export function updateRole(id: number, patch: Partial<Role>) {
  return client.put<unknown, { success: boolean }>(`/system/roles/${id}`, patch)
}

export function deleteRole(id: number) {
  return client.delete<unknown, { success: boolean }>(`/system/roles/${id}`)
}

// --- 权限 ---
export function getPermissions() {
  return client.get<unknown, Permission[]>('/system/permissions')
}
