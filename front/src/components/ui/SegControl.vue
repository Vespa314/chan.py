<template>
  <div class="seg">
    <button
      v-for="item in items"
      :key="item.value"
      class="seg__item"
      :class="{ 'is-active': modelValue === item.value }"
      @click="emit('update:modelValue', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
interface SegItem {
  label: string
  value: string | number
}

defineProps<{
  modelValue: string | number
  items: SegItem[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()
</script>
