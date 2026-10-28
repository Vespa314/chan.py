<template>
  <div class="stock-cell">
    <div class="stock-cell__code mono">{{ stock.code }}</div>
    <div class="stock-cell__name">{{ stock.name }}</div>
  </div>
</template>

<script setup lang="ts">
import type { Stock } from '@/api/types'

defineProps<{ stock: Stock }>()
</script>

<style scoped>
.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stock-cell__code {
  font-size: 12px;
  color: var(--text-secondary);
}
.stock-cell__name {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}
</style>
