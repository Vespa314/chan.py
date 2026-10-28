<template>
  <div class="page-layout">
    <!-- 左侧菜单栏 -->
    <Sidebar title="绩效">
      <TreeList
        group-label="方向"
        :items="directionItems"
        :active-key="activeDirection"
        @update:active-key="onDirectionChange"
      />
      <TreeList
        group-label="类型"
        :items="categoryItems"
        :active-key="activeCategory"
        @update:active-key="onCategoryChange"
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
      <div class="perf-page">
        <!-- 顶部统计行 -->
        <div class="stat-row">
          <StatCard label="总样本" :value="String(totalSamples)" foot="全部买卖点记录" />
          <StatCard
            label="综合胜率"
            :value="overallWinRateStr"
            :trend="overallWinRate >= 50 ? 'up' : 'down'"
            foot="盈利样本占比"
          />
          <StatCard
            label="平均盈亏"
            :value="avgPnlStr"
            :trend="avgPnl >= 0 ? 'up' : 'down'"
            foot="所有样本均值"
          />
          <StatCard
            label="盈利比"
            :value="profitRatioStr"
            foot="平均盈利 / 平均亏损"
          />
        </div>

        <!-- 胜率柱状图 -->
        <Panel title="胜率对比" sub="按买卖点类型 · 横线为 50% 分界">
          <div class="chart chart--grid" style="height:220px">
            <WinRateChart :data="winRateChartData" />
          </div>
        </Panel>

        <!-- 筛选区 -->
        <div class="toolbar reveal reveal--1">
          <el-select
            v-model="filterBspType"
            placeholder="全部类型"
            clearable
            style="width: 160px"
            @change="onFilterChange"
          >
            <el-option
              v-for="t in allBspTypes"
              :key="t"
              :label="t"
              :value="t"
            />
          </el-select>
          <el-select
            v-model="filterDirection"
            placeholder="全部方向"
            clearable
            style="width: 140px"
            @change="onFilterChange"
          >
            <el-option label="买" value="buy" />
            <el-option label="卖" value="sell" />
          </el-select>
          <span class="spacer"></span>
        </div>

        <!-- 绩效统计表 -->
        <Panel title="绩效统计" sub="按类型聚合" flush>
          <el-table
            v-loading="loading"
            :data="filteredStats"
            style="width: 100%"
            row-key="bsp_type"
            @row-click="onRowClick"
          >
            <el-table-column label="买卖点类型" width="120" align="center">
              <template #default="{ row }">
                <span class="badge" :class="isBuy(row.bsp_type) ? 'badge--rise' : 'badge--fall'">
                  {{ row.bsp_type }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="样本数" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num">{{ row.samples }}</span>
              </template>
            </el-table-column>
            <el-table-column label="胜率%" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num" :class="row.win_rate >= 50 ? 'text-rise' : 'text-fall'">
                  {{ row.win_rate.toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="平均盈亏%" width="120" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num" :class="row.avg_pnl >= 0 ? 'text-rise' : 'text-fall'">
                  {{ row.avg_pnl >= 0 ? '+' : '' }}{{ row.avg_pnl.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="盈亏比" width="100" align="right" class-name="col-num">
              <template #default="{ row }">
                <span class="num">{{ row.profit_ratio.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click.stop="onDrillDown(row)">
                  下钻
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState description="暂无绩效数据" />
            </template>
          </el-table>
        </Panel>
      </div>
    </div>

    <!-- 样本明细抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="样本明细"
      direction="rtl"
      size="520px"
    >
      <template v-if="drawerBspType">
        <div class="cell-stock" style="margin-bottom:16px">
          <span class="nm" style="font-size:16px;font-weight:600">{{ drawerBspType }} 样本明细</span>
          <span class="cd">
            样本数 {{ drawerSamples.length }} ·
            胜率 {{ drawerWinRate.toFixed(1) }}% ·
            平均盈亏 {{ drawerAvgPnl >= 0 ? '+' : '' }}{{ drawerAvgPnl.toFixed(2) }}%
          </span>
        </div>

        <div v-for="s in drawerSamples" :key="s.id" class="sample-item">
          <div class="cell-stock" style="flex:1">
            <span class="nm">{{ s.name }}</span>
            <span class="cd mono">{{ s.code }}</span>
          </div>
          <span class="num">{{ fmtDate(s.bsp_date) }}</span>
          <span class="num" :class="s.profit >= 0 ? 'text-rise' : 'text-fall'">
            {{ s.profit >= 0 ? '+' : '' }}{{ s.profit.toFixed(2) }}%
          </span>
        </div>
        <EmptyState v-if="drawerSamples.length === 0" description="暂无样本" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import TreeList from '@/components/ui/TreeList.vue'
import Panel from '@/components/ui/Panel.vue'
import StatCard from '@/components/ui/StatCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import WinRateChart from '@/components/charts/WinRateChart.vue'
import { getPerformanceStats, getPerformanceSamples } from '@/api/modules/performance'
import type { PerformanceStat, PerformanceSample } from '@/api/types'

// ---- 数据 ----
const loading = ref(false)
const stats = ref<PerformanceStat[]>([])
const samples = ref<PerformanceSample[]>([])

// ---- 筛选 ----
const filterBspType = ref('')
const filterDirection = ref('')
const activeDirection = ref('all')
const activeCategory = ref('all')
const activeKl = ref('all')

// ---- 侧栏 ----
const directionItems = [
  { key: 'all', label: '全部方向' },
  { key: 'buy', label: '买点绩效' },
  { key: 'sell', label: '卖点绩效' },
]
const categoryItems = [
  { key: 'all', label: '全部类型' },
  { key: '1', label: '第一类 (1B/1S)' },
  { key: '2', label: '第二类 (2B/2S)' },
  { key: '3', label: '第三类 (3B/3S)' },
]
const klTypeItems = [
  { key: 'all', label: '全部周期' },
  { key: 'D', label: '日线' },
  { key: '60m', label: '60分钟' },
  { key: '30m', label: '30分钟' },
]

function onDirectionChange(k: string) {
  activeDirection.value = k
  filterDirection.value = k === 'all' ? '' : k
}
function onCategoryChange(k: string) {
  activeCategory.value = k
  applyCategoryFilter()
}
function onKlChange(k: string) {
  activeKl.value = k
}

function applyCategoryFilter() {
  // 侧栏类型筛选只影响统计表展示
}

function onFilterChange() {
  // el-select 变化时同步侧栏
  if (filterDirection.value === '') activeDirection.value = 'all'
  else if (filterDirection.value === 'buy') activeDirection.value = 'buy'
  else activeDirection.value = 'sell'
}

// ---- 买卖点类型 ----
const allBspTypes = ['1B', '2B', '3B', '1S', '2S', 'L2B', 'L2S', '3S']

function isBuy(bspType: string) {
  return bspType.includes('B')
}

// ---- 统计表过滤 ----
const filteredStats = computed(() => {
  let list = stats.value
  if (filterBspType.value) {
    list = list.filter((r) => r.bsp_type === filterBspType.value)
  }
  if (filterDirection.value === 'buy') {
    list = list.filter((r) => isBuy(r.bsp_type))
  } else if (filterDirection.value === 'sell') {
    list = list.filter((r) => !isBuy(r.bsp_type))
  }
  if (activeCategory.value !== 'all') {
    list = list.filter((r) => r.bsp_type.startsWith(activeCategory.value))
  }
  return list
})

// ---- 胜率图数据（固定 8 柱）----
const winRateChartData = computed(() => {
  // 按 allBspTypes 顺序取，缺失补 0
  return allBspTypes.map((t) => {
    const s = stats.value.find((r) => r.bsp_type === t)
    return { name: t, winRate: s ? s.win_rate : 0 }
  })
})

// ---- 顶部统计 ----
const totalSamples = computed(() => {
  return stats.value.reduce((acc, r) => acc + r.samples, 0)
})

const overallWinRate = computed(() => {
  const list = stats.value
  const total = list.reduce((acc, r) => acc + r.samples, 0)
  if (total === 0) return 0
  const weighted = list.reduce((acc, r) => acc + r.samples * r.win_rate, 0)
  return +(weighted / total).toFixed(1)
})
const overallWinRateStr = computed(() => `${overallWinRate.value.toFixed(1)}%`)

const avgPnl = computed(() => {
  const list = stats.value
  const total = list.reduce((acc, r) => acc + r.samples, 0)
  if (total === 0) return 0
  const weighted = list.reduce((acc, r) => acc + r.samples * r.avg_pnl, 0)
  return +(weighted / total).toFixed(2)
})
const avgPnlStr = computed(() => `${avgPnl.value >= 0 ? '+' : ''}${avgPnl.value.toFixed(2)}%`)

const profitRatio = computed(() => {
  const list = stats.value
  if (list.length === 0) return 0
  const sum = list.reduce((acc, r) => acc + r.profit_ratio, 0)
  return +(sum / list.length).toFixed(2)
})
const profitRatioStr = computed(() => profitRatio.value.toFixed(2))

// ---- 抽屉 ----
const drawerVisible = ref(false)
const drawerBspType = ref('')
const drawerSamples = ref<PerformanceSample[]>([])

const drawerWinRate = computed(() => {
  const list = drawerSamples.value
  if (list.length === 0) return 0
  const wins = list.filter((s) => s.profit > 0).length
  return +((wins / list.length) * 100).toFixed(1)
})
const drawerAvgPnl = computed(() => {
  const list = drawerSamples.value
  if (list.length === 0) return 0
  const sum = list.reduce((acc, s) => acc + s.profit, 0)
  return +(sum / list.length).toFixed(2)
})

async function onDrillDown(row: PerformanceStat) {
  drawerBspType.value = row.bsp_type
  drawerVisible.value = true
  try {
    const list = await getPerformanceSamples(row.bsp_type)
    drawerSamples.value = list
  } catch {
    drawerSamples.value = []
  }
}

function onRowClick(row: PerformanceStat) {
  onDrillDown(row)
}

// ---- 工具 ----
function fmtDate(ts: number) {
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// ---- 加载 ----
async function loadAll() {
  loading.value = true
  try {
    const [st, sp] = await Promise.all([
      getPerformanceStats(),
      getPerformanceSamples(),
    ])
    stats.value = st
    samples.value = sp
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.perf-page {
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
.sample-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-base);
}
.sample-item:last-child {
  border-bottom: none;
}
</style>
