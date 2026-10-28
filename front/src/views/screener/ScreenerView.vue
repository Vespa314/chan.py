<template>
  <div class="page-layout">
    <!-- 左侧菜单栏 -->
    <aside class="panel sidebar reveal reveal--1">
      <div class="sidebar__head">
        选股
        <span class="spacer"></span>
      </div>
      <div class="tree">
        <div class="sidebar__group">
          <div class="sidebar__group-label">策略分类</div>
          <div
            class="tree__item"
            :class="{ 'is-active': filter === 'all' }"
            @click="filter = 'all'"
          >
            <el-icon class="tree__icon"><Operation /></el-icon>
            <span>全部策略</span>
            <span class="count">{{ strategies.length }}</span>
          </div>
          <div
            class="tree__item"
            :class="{ 'is-active': filter === 'buy' }"
            @click="filter = 'buy'"
          >
            <el-icon class="tree__icon"><Top /></el-icon>
            <span>买点策略</span>
            <span class="count">{{ buyCount }}</span>
          </div>
          <div
            class="tree__item"
            :class="{ 'is-active': filter === 'sell' }"
            @click="filter = 'sell'"
          >
            <el-icon class="tree__icon"><Bottom /></el-icon>
            <span>卖点策略</span>
            <span class="count">{{ sellCount }}</span>
          </div>
        </div>
        <div class="sidebar__group">
          <div class="sidebar__group-label">周期</div>
          <div
            v-for="kl in klOptions"
            :key="kl.value"
            class="tree__item"
            :class="{ 'is-active': klFilter === kl.value }"
            @click="klFilter = kl.value"
          >
            <el-icon class="tree__icon"><Calendar /></el-icon>
            <span>{{ kl.label }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主面板 -->
    <div class="main-panel">
      <div class="screener-page">
        <!-- 策略列表 -->
        <div class="panel reveal reveal--1">
          <div class="panel__head">
            选股策略
            <span class="spacer"></span>
            <button class="btn btn--primary btn--sm" @click="openCreate">
              <span class="icon-plus"></span> 新建策略
            </button>
          </div>
          <div v-loading="loading">
            <div
              v-for="s in filteredStrategies"
              :key="s.id"
              class="strategy-item"
            >
              <div class="main" style="flex: 1">
                <span class="t">{{ s.name }}</span>
                <span class="s">{{ strategySummary(s) }}</span>
              </div>
              <span class="num text-disabled" style="font-size: 12px">
                {{ s.last_run ? formatDateTime(s.last_run) : '未运行' }}
              </span>
              <span
                v-if="s.result_count !== undefined"
                class="badge badge--info"
              >
                结果 {{ s.result_count }}
              </span>
              <button
                class="btn btn--default btn--sm"
                :disabled="runningId === s.id"
                @click="onRun(s)"
              >
                {{ runningId === s.id ? '执行中' : '执行' }}
              </button>
              <button class="btn btn--ghost btn--sm" @click="openEdit(s)">编辑</button>
              <button
                class="btn btn--ghost btn--sm"
                style="color: var(--rise)"
                @click="onDelete(s)"
              >
                删除
              </button>
            </div>
            <EmptyState v-if="filteredStrategies.length === 0 && !loading" description="暂无策略，点击「新建策略」创建" />
          </div>
        </div>

        <!-- 扫描进度 -->
        <div v-if="runningId !== null" class="scan-hint reveal reveal--2">
          <span class="lbl">正在扫描「{{ runningStrategyName }}」…</span>
          <div class="progress"><div class="progress__bar" :style="{ width: progressPct + '%' }"></div></div>
          <span class="lbl num">耗时 {{ elapsedSec }}s</span>
        </div>

        <!-- 扫描结果表 -->
        <div v-if="results.length > 0" class="panel reveal reveal--3">
          <div class="panel__head">
            扫描结果
            <span class="panel__sub">匹配 {{ results.length }} 只</span>
            <span class="spacer"></span>
            <button class="btn btn--default btn--sm" @click="onBatchWatchlist">批量加入自选</button>
          </div>
          <div class="tbl-wrap">
            <el-table
              :data="results"
              @selection-change="onResultSelectionChange"
              row-key="code"
            >
              <el-table-column type="selection" width="44" />
              <el-table-column label="名称 / 编码" width="180">
                <template #default="{ row }">
                  <div class="cell-stock">
                    <span class="nm">{{ row.name }}</span>
                    <span class="cd mono">{{ row.code }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="股价" width="110" align="right">
                <template #default="{ row }">
                  <span class="num">{{ formatPrice(row.price) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="涨跌幅" width="120" align="right">
                <template #default="{ row }">
                  <ChangeBadge :value="row.change_pct" />
                </template>
              </el-table-column>
              <el-table-column label="行业" min-width="160">
                <template #default="{ row }">
                  <IndustryBadges :industries="row.industries" />
                </template>
              </el-table-column>
              <el-table-column label="匹配指标" min-width="140">
                <template #default="{ row }">
                  <span class="badge badge--rise">{{ row.bsp_type }} 买点</span>
                  <span class="badge badge--default">评分 {{ row.score }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110" align="right">
                <template #default="{ row }">
                  <button class="btn btn--default btn--sm" @click="onAddOneWatchlist(row)">加入自选</button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- 策略表单弹窗 -->
    <StrategyDialog
      v-model:visible="dialogVisible"
      :strategy="editingStrategy"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Operation, Top, Bottom, Calendar } from '@element-plus/icons-vue'
import IndustryBadges from '@/components/ui/IndustryBadges.vue'
import ChangeBadge from '@/components/ui/ChangeBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StrategyDialog from './StrategyDialog.vue'
import {
  getStrategies,
  deleteStrategy,
  runStrategy,
} from '@/api/modules/screener'
import { getFolders, addStock, type WatchFolder } from '@/api/modules/watchlist'
import type { Strategy, ScreenerResult } from '@/api/types'

const klOptions = [
  { label: '日线', value: 'D' },
  { label: '60分钟', value: '60m' },
  { label: '30分钟', value: '30m' },
  { label: '周线', value: 'W' },
]

const loading = ref(false)
const strategies = ref<Strategy[]>([])
const filter = ref<'all' | 'buy' | 'sell'>('all')
const klFilter = ref<string>('')

const buyCount = computed(() =>
  strategies.value.filter((s) => s.bsp_types.some((t) => t.includes('B'))).length,
)
const sellCount = computed(() =>
  strategies.value.filter((s) => s.bsp_types.some((t) => t.includes('S'))).length,
)

const filteredStrategies = computed(() => {
  let list = strategies.value
  if (filter.value === 'buy') {
    list = list.filter((s) => s.bsp_types.some((t) => t.includes('B')))
  } else if (filter.value === 'sell') {
    list = list.filter((s) => s.bsp_types.some((t) => t.includes('S')))
  }
  if (klFilter.value) {
    list = list.filter((s) => s.kl_type === klFilter.value)
  }
  return list
})

async function loadStrategies() {
  loading.value = true
  try {
    strategies.value = await getStrategies()
  } catch {
    strategies.value = []
  } finally {
    loading.value = false
  }
}

function strategySummary(s: Strategy) {
  const kl = klOptions.find((k) => k.value === s.kl_type)?.label || s.kl_type
  const types = s.bsp_types.join('/')
  const inds = s.industries.length ? ` · 行业 ${s.industries.join('/')}` : ''
  return `${kl} · ${types} · ${s.description}${inds}`
}

// ---- 执行 ----
const runningId = ref<number | null>(null)
const runningStrategyName = ref('')
const progressPct = ref(0)
const elapsedSec = ref(0)
const results = ref<ScreenerResult[]>([])
let progressTimer: ReturnType<typeof setInterval> | null = null
let elapsedTimer: ReturnType<typeof setInterval> | null = null

async function onRun(s: Strategy) {
  runningId.value = s.id
  runningStrategyName.value = s.name
  progressPct.value = 0
  elapsedSec.value = 0
  results.value = []
  // 模拟进度
  progressTimer = setInterval(() => {
    if (progressPct.value < 90) progressPct.value += 5
  }, 200)
  elapsedTimer = setInterval(() => {
    elapsedSec.value = +(elapsedSec.value + 0.2).toFixed(1)
  }, 200)
  try {
    const res = await runStrategy(s.id)
    progressPct.value = 100
    results.value = res.results
    ElMessage.success(`扫描完成，匹配 ${res.count} 只`)
  } catch {
    // 失败已处理
  } finally {
    if (progressTimer) clearInterval(progressTimer)
    if (elapsedTimer) clearInterval(elapsedTimer)
    setTimeout(() => {
      runningId.value = null
    }, 600)
  }
}

// ---- 删除 ----
async function onDelete(s: Strategy) {
  try {
    await ElMessageBox.confirm(`确定删除策略「${s.name}」吗？`, '删除策略', { type: 'warning' })
    await deleteStrategy(s.id)
    ElMessage.success('策略已删除')
    await loadStrategies()
  } catch {
    // 取消
  }
}

// ---- 弹窗 ----
const dialogVisible = ref(false)
const editingStrategy = ref<Strategy | null>(null)

function openCreate() {
  editingStrategy.value = null
  dialogVisible.value = true
}
function openEdit(s: Strategy) {
  editingStrategy.value = { ...s }
  dialogVisible.value = true
}

function onSaved() {
  dialogVisible.value = false
  loadStrategies()
}

// ---- 结果批量加入自选 ----
const resultSelection = ref<ScreenerResult[]>([])
function onResultSelectionChange(rows: ScreenerResult[]) {
  resultSelection.value = rows
}

async function onBatchWatchlist() {
  if (resultSelection.value.length === 0) {
    ElMessage.warning('请先选择要加入自选的股票')
    return
  }
  await doAddWatchlist(resultSelection.value.map((r) => r.code))
}

async function onAddOneWatchlist(row: ScreenerResult) {
  await doAddWatchlist([row.code])
}

async function doAddWatchlist(codes: string[]) {
  try {
    const folders: WatchFolder[] = await getFolders()
    if (folders.length === 0) {
      ElMessage.warning('请先创建自选文件夹')
      return
    }
    const { value } = await ElMessageBox.prompt(
      '请选择目标文件夹（输入文件夹 ID）',
      '加入自选',
      {
        inputType: 'number',
        inputValue: String(folders[0].id),
        inputValidator: (v: string) => {
          const id = Number(v)
          return folders.some((f) => f.id === id) || '文件夹 ID 无效'
        },
      },
    )
    const folderId = Number(value)
    const unique = Array.from(new Set(codes))
    await Promise.all(unique.map((c) => addStock(folderId, c)))
    ElMessage.success(`已加入 ${unique.length} 只到自选`)
  } catch {
    // 取消或失败
  }
}

// ---- 工具 ----
function formatPrice(v: number) {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function formatDateTime(ts: number) {
  const d = new Date(ts)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

onMounted(() => {
  loadStrategies()
})
</script>

<style scoped>
.screener-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
  flex: 1;
}
.strategy-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
  transition: background 0.12s ease;
}
.strategy-item:last-child {
  border-bottom: none;
}
.strategy-item:hover {
  background: var(--bg-surface-hover);
}
.strategy-item .main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.strategy-item .main .t {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.strategy-item .main .s {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.scan-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: var(--sp-md) var(--sp-lg);
  background: var(--bg-surface);
  border: 1px solid var(--border-base);
  border-radius: var(--r-lg);
}
.scan-hint .lbl {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.scan-hint .progress {
  flex: 1;
  max-width: 300px;
}
.cell-stock {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.cell-stock .nm {
  color: var(--text-primary);
  font-size: 13px;
}
.cell-stock .cd {
  color: var(--text-disabled);
  font-size: 11px;
}
</style>
