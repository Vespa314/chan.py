<template>
  <div class="alerts-page">
    <div class="panel">
      <el-tabs v-model="activeTab" class="alerts-tabs">
        <!-- 预警规则 -->
        <el-tab-pane label="预警规则" name="rules">
          <div class="toolbar">
            <span class="spacer"></span>
            <el-button v-permission="'manage'" type="primary" size="small" :icon="Plus" @click="openCreate">
              新建规则
            </el-button>
          </div>

          <el-table
            v-loading="rulesLoading"
            :data="rules"
            stripe
            empty-text="暂无预警规则"
            style="width: 100%"
          >
            <el-table-column label="规则名" prop="name" min-width="160" />
            <el-table-column label="股票代码" prop="code" width="130" class-name="mono-col" />
            <el-table-column label="股票名称" prop="stock_name" width="120" />
            <el-table-column label="条件" prop="condition" min-width="160" />
            <el-table-column label="级别" prop="kl_type" width="80" class-name="mono-col" />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  @change="(v: boolean) => onToggleRule(row, v)"
                />
              </template>
            </el-table-column>
            <el-table-column label="触发次数" prop="trigger_count" width="90" align="right" class-name="mono-col" />
            <el-table-column label="创建时间" width="120">
              <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="right">
              <template #default="{ row }">
                <el-button v-permission="'manage'" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button v-permission="'manage'" link type="danger" size="small" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 站内通知 -->
        <el-tab-pane :label="`站内通知${unreadCount ? ' · ' + unreadCount : ''}`" name="notices">
          <div class="toolbar">
            <span class="spacer"></span>
            <el-button size="small" :disabled="!unreadCount" @click="onMarkAllRead">全部已读</el-button>
          </div>

          <div v-loading="notiLoading" class="notice-list">
            <div v-if="!notifications.length" class="empty-wrap">
              <EmptyState description="暂无通知" />
            </div>
            <div
              v-for="n in notifications"
              :key="n.id"
              class="notice-item"
              :class="n.read ? 'is-read' : 'is-unread'"
            >
              <span class="unread-dot" :class="{ 'is-read': n.read }"></span>
              <div class="notice-body">
                <span class="notice-title">{{ n.message }}</span>
                <span class="notice-meta">{{ fmtDateTime(n.triggered_at) }} · 关联 {{ n.code }}</span>
              </div>
              <span class="badge" :class="ruleBadgeClass(n.rule_name)">{{ ruleTypeLabel(n.rule_name) }}</span>
              <el-button v-if="!n.read" link type="primary" size="small" @click="onMarkRead(n)">标记已读</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <RuleDialog v-model="dialogVisible" :rule="editingRule" @saved="loadRules" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import EmptyState from '@/components/ui/EmptyState.vue'
import RuleDialog from './RuleDialog.vue'
import * as alertsApi from '@/api/modules/alerts'
import type { AlertRule, AlertNotification } from '@/api/types'

const activeTab = ref<'rules' | 'notices'>('rules')
const rules = ref<AlertRule[]>([])
const notifications = ref<AlertNotification[]>([])
const rulesLoading = ref(false)
const notiLoading = ref(false)

const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

async function loadRules() {
  rulesLoading.value = true
  try {
    rules.value = await alertsApi.getRules()
  } catch {
    // handled
  } finally {
    rulesLoading.value = false
  }
}

async function loadNotifications() {
  notiLoading.value = true
  try {
    notifications.value = await alertsApi.getNotifications()
  } catch {
    // handled
  } finally {
    notiLoading.value = false
  }
}

onMounted(() => {
  loadRules()
  loadNotifications()
})

// --- 规则操作 ---
const dialogVisible = ref(false)
const editingRule = ref<AlertRule | null>(null)

function openCreate() {
  editingRule.value = null
  dialogVisible.value = true
}
function openEdit(row: AlertRule) {
  editingRule.value = { ...row }
  dialogVisible.value = true
}

async function onToggleRule(row: AlertRule, v: boolean) {
  try {
    await alertsApi.updateRule(row.id, { enabled: v })
    ElMessage.success(v ? '已启用' : '已停用')
  } catch {
    row.enabled = !v
  }
}

async function onDelete(row: AlertRule) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await alertsApi.deleteRule(row.id)
    ElMessage.success('已删除')
    loadRules()
  } catch {
    // handled
  }
}

// --- 通知操作 ---
async function onMarkRead(n: AlertNotification) {
  try {
    await alertsApi.markRead(n.id)
    n.read = true
  } catch {
    // handled
  }
}

async function onMarkAllRead() {
  try {
    await alertsApi.markAllRead()
    notifications.value.forEach((n) => (n.read = true))
    ElMessage.success('已全部标记为已读')
  } catch {
    // handled
  }
}

// --- 辅助 ---
function fmtDate(ts: number) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function fmtDateTime(ts: number) {
  const d = new Date(ts)
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function ruleTypeLabel(name: string) {
  if (name.includes('买点') || name.includes('顶分型') || name.includes('底背离')) return '买卖点'
  if (name.includes('突破') || name.includes('价格')) return '价格预警'
  return '预警'
}
function ruleBadgeClass(name: string) {
  if (name.includes('买点') || name.includes('顶分型') || name.includes('底背离')) return 'badge--rise'
  return 'badge--info'
}
</script>

<style scoped>
.alerts-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
  flex: 1;
}

.alerts-tabs :deep(.el-tabs__header) {
  margin: 0 0 0;
  padding: 0 var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
}
.alerts-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.alerts-tabs :deep(.el-tab-pane) {
  padding: 0 var(--sp-lg) var(--sp-lg);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--sp-sm);
  padding: var(--sp-md) 0;
}
.toolbar .spacer {
  flex: 1;
}

.mono-col {
  font-family: var(--font-mono);
}

/* 通知列表 */
.notice-list {
  padding: 4px 0;
  min-height: 120px;
}
.empty-wrap {
  padding: 32px 0;
}
.notice-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
}
.notice-item:last-child {
  border-bottom: none;
}
.notice-item.is-unread {
  background: var(--bg-surface-hover);
}
.notice-item.is-unread .notice-title {
  font-weight: 600;
}
.notice-item .notice-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.notice-item .notice-title {
  font-size: 13px;
  color: var(--text-primary);
}
.notice-item.is-read .notice-title {
  color: var(--text-secondary);
  font-weight: 400;
}
.notice-item .notice-meta {
  font-size: 11px;
  color: var(--text-disabled);
}
.unread-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-base);
  flex-shrink: 0;
}
.unread-dot.is-read {
  background: transparent;
}
</style>
