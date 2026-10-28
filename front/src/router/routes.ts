import type { RouteRecordRaw } from 'vue-router'

const Layout = () => import('@/components/layout/AppShell.vue')

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { layout: 'blank', public: true },
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/error/ForbiddenView.vue'),
    meta: { layout: 'blank', public: true },
  },
  {
    path: '/',
    redirect: '/kline',
  },
  {
    path: '/',
    component: Layout,
    children: [
      {
        path: 'kline',
        name: 'kline',
        component: () => import('@/views/kline/KLineView.vue'),
        meta: { title: 'K线分析', perm: 'menu:kline', navKey: 'kline' },
      },
      {
        path: 'watchlist',
        name: 'watchlist',
        component: () => import('@/views/watchlist/WatchlistView.vue'),
        meta: { title: '自选', perm: 'menu:watchlist', navKey: 'watchlist' },
      },
      {
        path: 'bsp',
        name: 'bsp',
        component: () => import('@/views/bsp/BspView.vue'),
        meta: { title: '买卖点', perm: 'menu:bsp', navKey: 'bsp' },
      },
      {
        path: 'monitor',
        name: 'monitor',
        component: () => import('@/views/monitor/MonitorView.vue'),
        meta: { title: '监控', perm: 'menu:monitor', navKey: 'monitor' },
      },
      {
        path: 'monitor/completed',
        name: 'monitor-completed',
        component: () => import('@/views/monitor/CompletedView.vue'),
        meta: { title: '监控完成', perm: 'menu:monitor', navKey: 'monitor-completed' },
      },
      {
        path: 'performance',
        name: 'performance',
        component: () => import('@/views/performance/PerformanceView.vue'),
        meta: { title: '绩效', perm: 'menu:performance', navKey: 'performance' },
      },
      {
        path: 'screener',
        name: 'screener',
        component: () => import('@/views/screener/ScreenerView.vue'),
        meta: { title: '选股', perm: 'menu:screener', navKey: 'screener' },
      },
      {
        path: 'alerts',
        name: 'alerts',
        component: () => import('@/views/alerts/AlertsView.vue'),
        meta: { title: '预警', perm: 'menu:alerts', navKey: 'alerts' },
      },
      {
        path: 'system',
        name: 'system',
        component: () => import('@/views/system/SystemView.vue'),
        meta: { title: '权限管理', perm: 'menu:system', navKey: 'system' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/kline',
  },
]
