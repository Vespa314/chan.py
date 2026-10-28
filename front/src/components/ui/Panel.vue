<template>
  <section class="panel">
    <header v-if="title || $slots.head" class="panel__head">
      <span v-if="title">{{ title }}</span>
      <span v-if="sub" class="panel__sub">{{ sub }}</span>
      <span class="spacer"></span>
      <slot name="head" />
    </header>
    <div class="panel__body" :class="{ 'panel__body--flush': flush }">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  sub?: string
  flush?: boolean
}>()
</script>

<style scoped>
.panel__body--flush {
  padding: 0;
}
</style>
