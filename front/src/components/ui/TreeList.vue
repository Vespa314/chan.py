<template>
  <div class="sidebar__group" v-if="items.length">
    <div v-if="groupLabel" class="sidebar__group-label">{{ groupLabel }}</div>
    <div
      v-for="item in items"
      :key="item.key"
      class="tree__item"
      :class="{ 'is-active': activeKey === item.key }"
      @click="emit('update:activeKey', item.key)"
    >
      <el-icon v-if="item.icon" class="tree__icon"><component :is="item.icon" /></el-icon>
      <span>{{ item.label }}</span>
      <span v-if="item.count !== undefined" class="count">{{ item.count }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface TreeItem {
  key: string
  label: string
  icon?: Component
  count?: number
}

defineProps<{
  groupLabel?: string
  items: TreeItem[]
  activeKey: string
}>()

const emit = defineEmits<{
  'update:activeKey': [key: string]
}>()
</script>
