<template>
  <nav class="topnav">
    <div class="topnav__brand">
      <span class="brand-mark"></span>
      <span class="brand-name">chan<span class="accent">.py</span></span>
      <span class="brand-cursor"></span>
      <span class="brand-sub">缠论量化</span>
    </div>

    <div class="topnav__menu">
      <router-link
        v-for="item in menuItems"
        :key="item.key"
        :to="item.to"
        class="menu-item"
        :class="{ 'is-active': isActive(item.key), 'menu-item--admin': item.admin }"
      >
        {{ item.label }}
        <span v-if="item.admin" class="admin-dot"></span>
      </router-link>
    </div>

    <el-dropdown trigger="click" @command="onUserCommand">
      <div class="topnav__user">
        <span class="user-avatar">{{ avatarText }}</span>
        <span class="user-name">{{ auth.user?.nickname || '未登录' }}</span>
        <el-icon class="user-chevron"><ArrowDown /></el-icon>
      </div>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="profile" :icon="User">{{ auth.user?.username }}</el-dropdown-item>
          <el-dropdown-item command="logout" :icon="SwitchButton" divided>退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown, User, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

interface MenuItem {
  key: string
  label: string
  to: string
  admin?: boolean
}

const allMenus: MenuItem[] = [
  { key: 'kline', label: 'K线', to: '/kline' },
  { key: 'watchlist', label: '自选', to: '/watchlist' },
  { key: 'bsp', label: '买卖点', to: '/bsp' },
  { key: 'monitor', label: '监控', to: '/monitor' },
  { key: 'monitor-completed', label: '完成', to: '/monitor/completed' },
  { key: 'performance', label: '绩效', to: '/performance' },
  { key: 'screener', label: '选股', to: '/screener' },
  { key: 'alerts', label: '预警', to: '/alerts' },
  { key: 'system', label: '权限管理', to: '/system', admin: true },
]

const menuItems = computed(() =>
  allMenus.filter((m) => auth.hasMenu(m.key)),
)

function isActive(key: string) {
  return route.meta.navKey === key
}

const avatarText = computed(() => {
  const name = auth.user?.nickname || auth.user?.username || '?'
  return name.charAt(0)
})

function onUserCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>
