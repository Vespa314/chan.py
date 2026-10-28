<template>
  <div class="page-layout">
    <!-- 左侧菜单栏 -->
    <Sidebar title="监控">
      <TreeList
        group-label="状态"
        :items="statusItems"
        :active-key="activeStatus"
        @update:active-key="onStatusChange"
      />
      <TreeList
        group-label="归因"
        :items="attrItems"
        :active-key="activeAttr"
        @update:active-key="onAttrChange"
      />
      <TreeList
        group-label="失败原因"
        :items="reasonItems"
        :active-key="activeReason"
        @update:active-key="onReasonChange"
      />
    </Sidebar>

    <!-- 右侧主面板 -->
    <div class="main-panel">
      <div class="completed-page">
        <!-- 顶部统计卡片行 -->
        <div class="stat-row">
          <StatCard label="完成总数" :value="String(completedList.length)" foot="历史已结算" />
          <StatCard
            label="胜率"
            :value="winRateStr"
            :trend="winRate >= 50 ? 'up' : 'down'"
            foot="盈利占比"
          />
          <StatCard
            label="平均盈利"
            :value="avgProfitStr"
            :trend="avgProfit >= 0 ? 'up' : 'down'"
            foot="所有完成标的"
          />
          <StatCard
            label="盈利比"
            :value="profitRatioStr"
            foot="平均盈利 / 平均亏损"
          />
        </div>

        <!-- 盈利走势图 -->
        <Panel title="盈利走势" sub="过去 14 日 · 全部完成标的">
          <div class="chart chart--grid" style="height:280px">
            <ProfitChart :series="profitSeries" />
          </div>
        </Panel>

        <!-- 操作工具条 -->
        <div class="toolbar reveal reveal--1">
          <el-input
            v-model="keyword"
            placeholder="搜索编码 / 名称"
            clearable
            style="width: 240px"
            :prefix-icon="Search"
            @input="onSearchInput"
            @clear="onSearchClear"
          />
          <span class="spacer"></span>
          <el-button
            type="primary"
            :loading="batchAnalyzing"
            :disabled="pendingItems.length === 0"
            @click="onBatchAnalyze"
          >
            大模型分析
          </el-button>
          <div v-if="batchAnalyzing" class="progress-hint">
            <span class="lbl">正在对盈利 &lt; 5% 的 {{ pendingItems.length }} 只标的做亏损归因…</span>
            <div class="progress">
              <div class="progress__bar" :style="{ width: batchProgress + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- 完成列表表格 -->
        <Panel title="监控完成记录" sub="已结算卖出" flush>
          <el-table
            v-loading="loading"
            :data="pagedList"
            style="width: 100%"
            row-key="id"
          >
            <el-table-column label="名称 / 编码" min-width="150">
              <template #default="{ row }">
                <div class="cell-stock">
                  <span class="nm">{{ row.name }}</span>
                  <span class="cd mono">{{ row.code }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="买卖点" width="80" align="center">
              <template #default="{ row }">
                <span class="badge" :class="row.direction === 'buy' ? 'badge--rise' : 'badge--fall'">
                  {{ row.bsp_type }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="方向" width="70" align="center">
              <template #default="{ row }">
                <span class="badge" :class="row.direction === 'buy' ? 'badge--rise' : 'badge--fall'">
                  {{ row.direction === 'buy' ? '买' : '卖' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="买卖点价格" width="110" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num">{{ fmtPrice(row.bsp_price) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结束价格" width="110" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num">{{ fmtPrice(row.end_price) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="收益率" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num" :class="row.profit >= 0 ? 'text-rise' : 'text-fall'">
                  {{ row.profit >= 0 ? '+' : '' }}{{ row.profit.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="买卖点日期" width="120" align="center">
              <template #default="{ row }">
                <span class="num">{{ fmtDate(row.bsp_date) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结束日期" width="120" align="center">
              <template #default="{ row }">
                <span class="num">{{ fmtDate(row.end_date) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="归因" min-width="160">
              <template #default="{ row }">
                <span v-if="row.ai_analyzed" class="badge badge--accent">已归因</span>
                <span v-else class="badge badge--disabled">未归因</span>
              </template>
            </el-table-column>
            <el-table-column label="AI分析" width="100" align="center">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  :loading="analyzingId === row.id"
                  @click="onAnalyze(row)"
                >
                  {{ row.ai_analyzed ? '重新分析' : '大模型分析' }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="right" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="onViewDetail(row)">
                  查看归因
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState description="暂无完成记录" />
            </template>
          </el-table>

          <div v-if="filteredList.length > pageSize" class="pager-wrap">
            <el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              :total="filteredList.length"
              layout="prev, pager, next, total"
              background
              small
            />
          </div>
        </Panel>

        <!-- 失败原因汇总 -->
        <Panel title="失败原因汇总" sub="盈利 < 5% 的标的 · 大模型归因">
          <div class="sum-list">
            <div v-for="item in lossItems" :key="item.id" class="sum-item">
              <span class="badge" :class="reasonBadgeClass(item)">{{ reasonCategory(item) }}</span>
              <div class="cell-stock" style="min-width:150px">
                <span class="nm">{{ item.name }}</span>
                <span class="cd mono">{{ item.code }}</span>
              </div>
              <div class="reason">
                <span class="t">{{ item.attribution }}</span>
                <span class="s">证据：{{ reasonCategory(item) }} · {{ fmtDate(item.end_date) }}</span>
              </div>
              <span class="spacer"></span>
              <span class="num text-fall">{{ item.profit >= 0 ? '+' : '' }}{{ item.profit.toFixed(2) }}%</span>
              <el-button link type="primary" size="small" @click="onViewDetail(item)">
                查看详情
              </el-button>
            </div>
            <EmptyState v-if="lossItems.length === 0" description="暂无亏损归因记录" />
          </div>
        </Panel>
      </div>
    </div>

    <!-- 归因详情抽屉 -->
    <SampleDrawer v-model="drawerVisible" :item="drawerItem" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import TreeList from '@/components/ui/TreeList.vue'
import Panel from '@/components/ui/Panel.vue'
import StatCard from '@/components/ui/StatCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ProfitChart from '@/components/charts/ProfitChart.vue'
import SampleDrawer from './SampleDrawer.vue'
import { usePagination } from '@/composables/usePagination'
import { getCompletedList, getProfitSeries, analyzeMonitor } from '@/api/modules/monitor'
import type { CompletedItem } from '@/api/types'

const router = useRouter()
const route = useRoute()

// ---- 数据 ----
const loading = ref(false)
const completedList = ref<CompletedItem[]>([])
const profitSeries = ref<{ date: string; value: number }[]>([])

// ---- 筛选 ----
const keyword = ref('')
const activeStatus = ref('completed')
const activeAttr = ref('all')
const activeReason = ref('all')

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
  }, 300)
}
function onSearchClear() {
  keyword.value = ''
  page.value = 1
}

// ---- 分页 ----
const { page, pageSize } = usePagination(20)

// ---- 侧栏 ----
const statusItems = [
  { key: 'monitoring', label: '监控中' },
  { key: 'completed', label: '已完成' },
]
const attrItems = [
  { key: 'all', label: '全部' },
  { key: 'analyzed', label: '已归因' },
  { key: 'pending', label: '未归因' },
]
const reasonItems = [
  { key: 'all', label: '全部' },
  { key: 'theory', label: '缠论失效' },
  { key: 'logic', label: '计算逻辑错误' },
]

function onStatusChange(k: string) {
  if (k === 'monitoring') {
    router.push('/monitor')
    return
  }
  activeStatus.value = k
  page.value = 1
}
function onAttrChange(k: string) {
  activeAttr.value = k
  page.value = 1
}
function onReasonChange(k: string) {
  activeReason.value = k
  page.value = 1
}

// ---- 过滤 ----
const filteredList = computed(() => {
  let list = completedList.value
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter((r) => r.code.toLowerCase().includes(kw) || r.name.toLowerCase().includes(kw))
  }
  if (activeAttr.value === 'analyzed') {
    list = list.filter((r) => r.ai_analyzed)
  } else if (activeAttr.value === 'pending') {
    list = list.filter((r) => !r.ai_analyzed)
  }
  if (activeReason.value !== 'all') {
    list = list.filter((r) => reasonCategory(r) === (activeReason.value === 'theory' ? '缠论失效' : '计算逻辑错误'))
  }
  return list
})

const pagedList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

// ---- 统计 ----
const winRate = computed(() => {
  const list = completedList.value
  if (list.length === 0) return 0
  const wins = list.filter((r) => r.profit > 0).length
  return +((wins / list.length) * 100).toFixed(1)
})
const winRateStr = computed(() => `${winRate.value.toFixed(1)}%`)

const avgProfit = computed(() => {
  const list = completedList.value
  if (list.length === 0) return 0
  const sum = list.reduce((acc, r) => acc + r.profit, 0)
  return +(sum / list.length).toFixed(2)
})
const avgProfitStr = computed(() => `${avgProfit.value >= 0 ? '+' : ''}${avgProfit.value.toFixed(2)}%`)

const profitRatio = computed(() => {
  const list = completedList.value
  const wins = list.filter((r) => r.profit > 0)
  const losses = list.filter((r) => r.profit < 0)
  if (wins.length === 0 || losses.length === 0) return wins.length / (losses.length || 1)
  const avgWin = wins.reduce((a, r) => a + r.profit, 0) / wins.length
  const avgLoss = Math.abs(losses.reduce((a, r) => a + r.profit, 0) / losses.length)
  return +(avgWin / (avgLoss || 1)).toFixed(2)
})
const profitRatioStr = computed(() => profitRatio.value.toFixed(2))

// ---- 失败原因汇总（profit < 5%）----
const lossItems = computed(() => {
  return completedList.value.filter((r) => r.profit < 5)
})

// ---- 待分析标的 ----
const pendingItems = computed(() => {
  return completedList.value.filter((r) => !r.ai_analyzed && r.profit < 5)
})

// ---- 工具 ----
function fmtPrice(v: number) {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtDate(ts: number) {
  const d = new Date(ts)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}

function reasonCategory(item: CompletedItem): string {
  const t = item.attribution || ''
  if (/包含|逻辑|计算|中枢区间|端点/.test(t)) return '计算逻辑错误'
  return '缠论失效'
}
function reasonBadgeClass(item: CompletedItem) {
  return reasonCategory(item) === '计算逻辑错误' ? 'badge--info' : 'badge--warning'
}

// ---- 抽屉 ----
const drawerVisible = ref(false)
const drawerItem = ref<CompletedItem | null>(null)

function onViewDetail(row: CompletedItem) {
  drawerItem.value = row
  drawerVisible.value = true
}

// ---- AI 分析 ----
const analyzingId = ref<number | null>(null)
async function onAnalyze(row: CompletedItem) {
  analyzingId.value = row.id
  try {
    await analyzeMonitor(row.id)
    row.ai_analyzed = true
    ElMessage.success('归因分析完成')
  } finally {
    analyzingId.value = null
  }
}

// ---- 批量分析 ----
const batchAnalyzing = ref(false)
const batchProgress = ref(0)
async function onBatchAnalyze() {
  const targets = pendingItems.value
  if (targets.length === 0) {
    ElMessage.info('没有待分析的标的')
    return
  }
  batchAnalyzing.value = true
  batchProgress.value = 0
  try {
    for (let i = 0; i < targets.length; i++) {
      const row = targets[i]
      await analyzeMonitor(row.id)
      row.ai_analyzed = true
      batchProgress.value = Math.round(((i + 1) / targets.length) * 100)
    }
    ElMessage.success(`完成 ${targets.length} 只标的的归因分析`)
  } finally {
    batchAnalyzing.value = false
  }
}

// ---- 加载 ----
async function loadAll() {
  loading.value = true
  try {
    const [cl, ps] = await Promise.all([
      getCompletedList(),
      getProfitSeries(),
    ])
    completedList.value = cl
    profitSeries.value = ps
    // 若从监控页带 code 跳入，定位该行
    const code = route.query.code as string | undefined
    if (code) {
      const idx = cl.findIndex((r) => r.code === code)
      if (idx >= 0) {
        const targetPage = Math.floor(idx / pageSize.value) + 1
        page.value = targetPage
      }
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.completed-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
  flex: 1;
}
.stat-row {
  display: flex;
  gap: var(--sp-lg);
}
.stat-row > * {
  flex: 1;
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
.progress-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 360px;
}
.progress-hint .lbl {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.progress-hint .progress {
  flex: 1;
}
.pager-wrap {
  display: flex;
  justify-content: flex-end;
  padding: var(--sp-md) var(--sp-lg);
}
.sum-list {
  padding: 4px 0;
}
.sum-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
}
.sum-item:last-child {
  border-bottom: none;
}
.sum-item .reason {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.sum-item .reason .t {
  font-size: 13px;
  color: var(--text-primary);
}
.sum-item .reason .s {
  font-size: 11px;
  color: var(--text-disabled);
}
</style>
