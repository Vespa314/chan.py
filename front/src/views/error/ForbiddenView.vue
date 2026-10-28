<template>
  <div class="forbidden-page">
    <div class="forbidden-code">403</div>
    <div class="forbidden-text">没有权限访问此页面</div>
    <el-button type="primary" @click="$router.push('/kline')">返回首页</el-button>
  </div>
</template>

<style scoped>
.forbidden-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: var(--bg-base);
}
.forbidden-code {
  font-family: var(--font-mono);
  font-size: 72px;
  font-weight: 700;
  color: var(--text-disabled);
}
.forbidden-text {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}
</style>
