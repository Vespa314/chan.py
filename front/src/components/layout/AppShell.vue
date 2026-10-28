<template>
  <div class="app-shell">
    <Topnav />
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import Topnav from './Topnav.vue'
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
