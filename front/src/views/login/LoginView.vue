<template>
  <div class="login-page">
    <div class="login-bg-grid"></div>
    <div class="login-card">
      <div class="login-brand">
        <span class="brand-mark"></span>
        <span class="brand-name">chan<span class="accent">.py</span></span>
        <span class="brand-cursor"></span>
      </div>
      <div class="login-sub">缠论量化分析平台</div>

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onLogin" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="onLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="onLogin">
          登 录
        </el-button>
      </el-form>

      <div class="login-hint">
        <div class="login-hint__title">测试账号</div>
        <div class="login-hint__row" v-for="u in testUsers" :key="u.username" @click="fillUser(u)">
          <span class="mono">{{ u.username }} / {{ u.password }}</span>
          <span class="login-hint__role">{{ u.role }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const testUsers = [
  { username: 'admin', password: 'admin123', role: '管理员（全权限）' },
  { username: 'trader', password: 'trader123', role: '交易员（无系统管理）' },
  { username: 'viewer', password: 'viewer123', role: '观察者（仅K线/自选）' },
]

function fillUser(u: { username: string; password: string }) {
  form.username = u.username
  form.password = u.password
}

async function onLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await auth.login(form.username, form.password)
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || '/kline'
      router.push(redirect)
    } catch {
      // 错误已由 axios 拦截器处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
  overflow: hidden;
}

.login-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 50%, #000 30%, transparent 80%);
}

.login-card {
  position: relative;
  width: 380px;
  padding: 40px 32px 28px;
  background: var(--bg-surface);
  border: 1px solid var(--border-base);
  border-radius: var(--r-lg);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.login-brand {
  display: flex;
  align-items: center;
  gap: var(--sp-sm);
  margin-bottom: 4px;
}
.login-sub {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 28px;
  padding-left: 2px;
}

.login-form {
  margin-bottom: 20px;
}
.login-btn {
  width: 100%;
  height: 40px;
  font-size: 14px;
  letter-spacing: 0.1em;
}

.login-hint {
  border-top: 1px solid var(--border-base);
  padding-top: 16px;
}
.login-hint__title {
  font-size: 11px;
  color: var(--text-disabled);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.login-hint__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  border-radius: var(--r-sm);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: background 0.15s;
}
.login-hint__row:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}
.login-hint__role {
  font-size: 11px;
  color: var(--text-disabled);
}
</style>
