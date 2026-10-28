<template>
  <span class="industry-badges">
    <span v-for="ind in industries" :key="ind" class="badge badge--ghost">{{ ind }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{ industries: string[] }>()
</script>

<style scoped>
.industry-badges {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
