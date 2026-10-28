<template>
  <router-view v-slot="{ Component, route }">
    <transition name="router-fade" mode="out-in">
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
// App.vue — 仅作路由出口 + 过渡。布局由各路由 meta.layout 决定（blank / app）
</script>
