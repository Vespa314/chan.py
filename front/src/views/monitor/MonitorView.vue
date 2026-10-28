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
        group-label="盈利"
        :items="profitItems"
        :active-key="activeProfit"
        @update:active-key="onProfitChange"
      />
      <TreeList
        group-label="周期"
        :items="klTypeItems"
        :active-key="activeKl"
        @update:active-key="onKlChange"
      />
    </Sidebar>

    <!-- 右侧主面板 -->
    <div class="main-panel">
      <div class="monitor-page">
        <!-- 汇总卡 -->
        <div class="stat-row">
          <StatCard
            label="总体盈利（%）"
            :value="totalProfitStr"
            :foot="`${monitorList.length} 只监控中 · 加权平均`"
            :trend="totalProfit >= 0 ? 'up' : 'down'"
            accent
          />
          <StatCard
            label="监控中数量"
            :value="String(monitorList.length)"
            foot="实时跟踪"
          />
          <StatCard
            label="累计完成"
            :value="String(completedCount)"
            foot="历史已结算监控"
          />
        </div>

        <!-- 盈利走势图 -->
        <Panel title="盈利走势" sub="过去 14 日 · 全部监控标的">
          <template #head>
            <SegControl v-model="profitSeg" :items="segItems" />
          </template>
          <div class="chart chart--grid" style="height:280px">
            <template v-if="profitSeg === 'summary'">
              <ProfitChart :series="profitSeries" />
            </template>
            <template v-else>
              <div class="single-stock-toolbar">
                <el-select
                  v-model="singleStockId"
                  placeholder="选择标的"
                  filterable
                  size="small"
                  style="width: 200px"
                >
                  <el-option
                    v-for="r in monitorList"
                    :key="r.id"
                    :label="`${r.name} (${r.code})`"
                    :value="r.id"
                  />
                </el-select>
              </div>
              <ProfitChart v-if="singleStockId" :series="singleStockSeries" />
              <EmptyState v-else description="请选择标的查看单只走势" />
            </template>
          </div>
        </Panel>

        <!-- 筛选 + 表格 -->
        <div class="toolbar reveal reveal--4">
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
          <el-radio-group v-model="tabMode" @change="onTabChange">
            <el-radio-button value="monitoring">监控中</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
          </el-radio-group>
        </div>

        <Panel flush>
          <el-table
            v-loading="loading"
            :data="pagedList"
            style="width: 100%"
            row-key="id"
            @row-dblclick="onRowDblClick"
          >
            <el-table-column label="名称 / 编码" min-width="150">
              <template #default="{ row }">
                <div class="cell-stock">
                  <span class="nm">{{ row.name }}</span>
                  <span class="cd mono">{{ row.code }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="行业" min-width="120">
              <template #default="{ row }">
                <IndustryBadges :industries="row.industries" />
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
            <el-table-column label="当前价" width="110" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num">{{ fmtPrice(row.current_price) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <ChangeBadge :value="row.change_pct" />
              </template>
            </el-table-column>
            <el-table-column label="最大盈利" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num text-rise">{{ row.max_profit >= 0 ? '+' : '' }}{{ row.max_profit.toFixed(2) }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="最大回撤" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num text-fall">{{ row.max_drawdown.toFixed(2) }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="级别" width="80" align="center">
              <template #default="{ row }">
                <span class="num">{{ klLabel(row.kl_type) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="right" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'monitoring'"
                  link
                  type="danger"
                  size="small"
                  :loading="endingId === row.id"
                  @click="onEnd(row)"
                >
                  手动结束
                </el-button>
                <el-button link type="primary" size="small" @click="onViewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState description="暂无监控记录" />
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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import TreeList from '@/components/ui/TreeList.vue'
import Panel from '@/components/ui/Panel.vue'
import StatCard from '@/components/ui/StatCard.vue'
import SegControl from '@/components/ui/SegControl.vue'
import ChangeBadge from '@/components/ui/ChangeBadge.vue'
import IndustryBadges from '@/components/ui/IndustryBadges.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ProfitChart from '@/components/charts/ProfitChart.vue'
import { usePagination } from '@/composables/usePagination'
import { getMonitorList, getCompletedList, getProfitSeries, endMonitor } from '@/api/modules/monitor'
import type { MonitorItem, CompletedItem } from '@/api/types'

const router = useRouter()

// ---- 数据 ----
const loading = ref(false)
const monitorList = ref<MonitorItem[]>([])
const completedList = ref<CompletedItem[]>([])
const completedCount = ref(0)
const profitSeries = ref<{ date: string; value: number }[]>([])

// ---- 筛选 ----
const keyword = ref('')
const tabMode = ref<'monitoring' | 'completed'>('monitoring')
const activeStatus = ref('monitoring')
const activeProfit = ref('all')
const activeKl = ref('all')

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
const { page, pageSize, setTotal } = usePagination(20)

// ---- 监控中/已完成切换 ----
function onTabChange(v: string | number | boolean) {
  const val = String(v)
  if (val === 'completed') {
    router.push('/monitor/completed')
    return
  }
  activeStatus.value = 'monitoring'
  page.value = 1
}

// ---- 侧栏 ----
const statusItems = [
  { key: 'monitoring', label: '监控中', count: 0 },
  { key: 'completed', label: '已完成', count: 0 },
]
const profitItems = [
  { key: 'all', label: '全部' },
  { key: 'profit', label: '盈利' },
  { key: 'loss', label: '亏损' },
]
const klTypeItems = [
  { key: 'all', label: '全部周期' },
  { key: 'D', label: '日线' },
  { key: '60m', label: '60分钟' },
  { key: '30m', label: '30分钟' },
]

function onStatusChange(k: string) {
  activeStatus.value = k
  if (k === 'completed') router.push('/monitor/completed')
  else { tabMode.value = 'monitoring'; page.value = 1 }
}
function onProfitChange(k: string) {
  activeProfit.value = k
  page.value = 1
}
function onKlChange(k: string) {
  activeKl.value = k
  page.value = 1
}

// ---- 盈利走势 seg ----
const profitSeg = ref('summary')
const segItems = [
  { label: '汇总', value: 'summary' },
  { label: '单只', value: 'single' },
]

// ---- 单只标的走势 ----
const singleStockId = ref<number | null>(null)
const singleStockSeries = computed(() => {
  if (!singleStockId.value) return []
  const row = monitorList.value.find((r) => r.id === singleStockId.value)
  if (!row) return []
  // 基于买卖点价格 → 当前价 生成 14 日模拟走势
  const start = row.bsp_price
  const end = row.current_price
  const series: { date: string; value: number }[] = []
  for (let i = 13; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000)
    const ratio = (13 - i) / 13
    const noise = (Math.sin(i * 1.7) * 1.5)
    const v = +(((start * (1 + ratio * ((end - start) / start)) + noise) - start) / start * 100).toFixed(2)
    series.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      value: v,
    })
  }
  return series
})

// ---- 过滤 ----
const filteredList = computed<MonitorItem[]>(() => {
  let list = monitorList.value
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter((r) => r.code.toLowerCase().includes(kw) || r.name.toLowerCase().includes(kw))
  }
  if (activeKl.value !== 'all') {
    list = list.filter((r) => r.kl_type === activeKl.value)
  }
  if (activeProfit.value === 'profit') {
    list = list.filter((r) => r.max_profit >= 0)
  } else if (activeProfit.value === 'loss') {
    list = list.filter((r) => r.max_profit < 0)
  }
  return list
})

const pagedList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

// ---- 汇总 ----
const totalProfit = computed(() => {
  const list = monitorList.value
  if (list.length === 0) return 0
  const sum = list.reduce((acc, r) => acc + r.max_profit, 0)
  return +(sum / list.length).toFixed(2)
})
const totalProfitStr = computed(() => `${totalProfit.value >= 0 ? '+' : ''}${totalProfit.value.toFixed(2)}%`)

// ---- 工具 ----
function fmtPrice(v: number) {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function klLabel(k: string) {
  const m: Record<string, string> = { D: '日线', '60m': '60分钟', '30m': '30分钟', '15m': '15分钟' }
  return m[k] || k
}

// ---- 操作 ----
const endingId = ref<number | null>(null)
async function onEnd(row: MonitorItem) {
  try {
    await ElMessageBox.confirm(`确认手动结束「${row.name}」的监控？`, '提示', {
      type: 'warning',
      confirmButtonText: '确认结束',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  endingId.value = row.id
  try {
    await endMonitor(row.id)
    monitorList.value = monitorList.value.filter((r) => r.id !== row.id)
    ElMessage.success('已结束监控')
  } finally {
    endingId.value = null
  }
}

function onViewDetail(row: MonitorItem) {
  router.push({ path: '/monitor/completed', query: { code: row.code } })
}

function onRowDblClick(row: MonitorItem) {
  onViewDetail(row)
}

// ---- 加载 ----
async function loadAll() {
  loading.value = true
  try {
    const [ml, cl, ps] = await Promise.all([
      getMonitorList(),
      getCompletedList(),
      getProfitSeries(),
    ])
    monitorList.value = ml
    completedList.value = cl
    completedCount.value = cl.length
    profitSeries.value = ps
    statusItems[0].count = ml.length
    statusItems[1].count = cl.length
    setTotal(ml.length)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.monitor-page {
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
.pager-wrap {
  display: flex;
  justify-content: flex-end;
  padding: var(--sp-md) var(--sp-lg);
}
.single-stock-toolbar {
  position: absolute;
  top: 10px;
  right: 14px;
  z-index: 10;
}
</style>
