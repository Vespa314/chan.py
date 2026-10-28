<template>
  <div class="stat" :class="{ 'stat--accent': accent }">
    <div class="stat__label">{{ label }}</div>
    <div class="stat__value mono" :class="valueClass">
      <slot>{{ value }}</slot>
    </div>
    <div v-if="foot" class="stat__foot">{{ foot }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value?: string | number
  foot?: string
  accent?: boolean
  trend?: 'up' | 'down' | 'flat'
}>()

const valueClass = computed(() => {
  if (props.trend === 'up') return 'text-rise'
  if (props.trend === 'down') return 'text-fall'
  return ''
})
</script>
