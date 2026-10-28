import type { User, Role, Permission } from '@/api/types'

export const permissions: Permission[] = [
  { id: 1, code: 'menu:kline', name: 'K线分析', category: '菜单' },
  { id: 2, code: 'menu:watchlist', name: '自选', category: '菜单' },
  { id: 3, code: 'menu:bsp', name: '买卖点', category: '菜单' },
  { id: 4, code: 'menu:monitor', name: '监控', category: '菜单' },
  { id: 5, code: 'menu:performance', name: '绩效', category: '菜单' },
  { id: 6, code: 'menu:screener', name: '选股', category: '菜单' },
  { id: 7, code: 'menu:alerts', name: '预警', category: '菜单' },
  { id: 8, code: 'menu:system', name: '权限管理', category: '菜单' },
  { id: 9, code: 'manage', name: '管理操作', category: '管理' },
]

export const roles: Role[] = [
  {
    id: 1, name: '管理员', code: 'admin', description: '拥有所有权限',
    user_count: 1,
    perms: permissions.map((p) => p.code),
  },
  {
    id: 2, name: '交易员', code: 'trader', description: '可访问业务页面，无系统管理权限',
    user_count: 1,
    perms: ['menu:kline', 'menu:watchlist', 'menu:bsp', 'menu:monitor', 'menu:performance', 'menu:screener', 'menu:alerts'],
  },
  {
    id: 3, name: '观察者', code: 'viewer', description: '仅可查看K线和自选',
    user_count: 1,
    perms: ['menu:kline', 'menu:watchlist'],
  },
]

export const users: User[] = [
  {
    id: 1, username: 'admin', nickname: '管理员', role: 'admin', role_name: '管理员',
    status: 'active', created_at: Date.now() - 86400000 * 90, last_login: Date.now() - 3600000,
  },
  {
    id: 2, username: 'trader', nickname: '交易员', role: 'trader', role_name: '交易员',
    status: 'active', created_at: Date.now() - 86400000 * 30, last_login: Date.now() - 7200000,
  },
  {
    id: 3, username: 'viewer', nickname: '观察者', role: 'viewer', role_name: '观察者',
    status: 'active', created_at: Date.now() - 86400000 * 7, last_login: Date.now() - 86400000,
  },
]

let nextUserId = 4
let nextRoleId = 4

export function addUser(u: Omit<User, 'id' | 'created_at'>): User {
  const user = { ...u, id: nextUserId++, created_at: Date.now() }
  users.push(user)
  return user
}
export function updateUser(id: number, patch: Partial<User>) {
  const idx = users.findIndex((u) => u.id === id)
  if (idx >= 0) users[idx] = { ...users[idx], ...patch }
}
export function removeUser(id: number) {
  const idx = users.findIndex((u) => u.id === id)
  // admin 不可删
  if (idx >= 0 && users[idx].role !== 'admin') users.splice(idx, 1)
  return idx >= 0 && users[idx]?.role !== 'admin'
}
export function addRole(r: Omit<Role, 'id' | 'user_count'>): Role {
  const role = { ...r, id: nextRoleId++, user_count: 0 }
  roles.push(role)
  return role
}
export function updateRole(id: number, patch: Partial<Role>) {
  const idx = roles.findIndex((r) => r.id === id)
  if (idx >= 0) roles[idx] = { ...roles[idx], ...patch }
}
export function removeRole(id: number) {
  const idx = roles.findIndex((r) => r.id === id)
  if (idx >= 0 && roles[idx].code !== 'admin') roles.splice(idx, 1)
  return idx >= 0 && roles[idx]?.code !== 'admin'
}
