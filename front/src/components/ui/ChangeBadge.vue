<template>
  <span class="change-badge mono" :class="cls">
    {{ sign }}{{ Math.abs(value).toFixed(2) }}%
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()

const cls = computed(() => {
  if (props.value > 0) return 'change-badge--up'
  if (props.value < 0) return 'change-badge--down'
  return 'change-badge--flat'
})

const sign = computed(() => (props.value > 0 ? '+' : ''))
</script>

<style scoped>
.change-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--r-sm);
}
.change-badge--up {
  color: var(--rise);
  background: var(--rise-dim);
}
.change-badge--down {
  color: var(--fall);
  background: var(--fall-dim);
}
.change-badge--flat {
  color: var(--text-secondary);
  background: var(--bg-surface-hover);
}
</style>
