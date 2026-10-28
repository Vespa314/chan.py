<template>
  <aside class="sidebar">
    <div class="sidebar__head">
      <span>{{ title }}</span>
      <span class="spacer"></span>
      <slot name="action" />
    </div>
    <div class="tree">
      <slot />
    </div>
  </aside>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>
