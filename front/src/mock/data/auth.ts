import type { UserInfo } from '@/stores/auth'

export interface MockUser extends UserInfo {
  password: string
  perms: string[]
}

/** 3 个 mock 用户 — design.md D16 RBAC */
export const mockUsers: MockUser[] = [
  {
    id: 1,
    username: 'admin',
    password: 'admin123',
    nickname: '管理员',
    role: 'admin',
    status: 'active',
    perms: [
      'menu:kline', 'menu:watchlist', 'menu:bsp', 'menu:monitor',
      'menu:performance', 'menu:screener', 'menu:alerts', 'menu:system',
      'manage',
    ],
  },
  {
    id: 2,
    username: 'trader',
    password: 'trader123',
    nickname: '交易员',
    role: 'trader',
    status: 'active',
    perms: [
      'menu:kline', 'menu:watchlist', 'menu:bsp', 'menu:monitor',
      'menu:performance', 'menu:screener', 'menu:alerts',
    ],
  },
  {
    id: 3,
    username: 'viewer',
    password: 'viewer123',
    nickname: '观察者',
    role: 'viewer',
    status: 'active',
    perms: ['menu:kline', 'menu:watchlist'],
  },
]

export function findUser(username: string): MockUser | undefined {
  return mockUsers.find((u) => u.username === username)
}
