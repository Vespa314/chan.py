<template>
  <div class="kline-page">
    <!-- 顶栏工具栏 — design.md D9 -->
    <header class="topbar reveal">
      <el-input
        v-model="codeInput"
        class="code-field"
        placeholder="股票代码 如 sz.000001"
        :prefix-icon="SearchIcon"
        size="default"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" size="default" :loading="loading" @click="handleSearch">
        搜索
      </el-button>

      <el-select v-model="period" size="default" class="period-select" @change="handleSearch">
        <el-option label="1分钟" value="1m" />
        <el-option label="5分钟" value="5m" />
        <el-option label="1小时" value="1h" />
        <el-option label="日线" value="1d" />
        <el-option label="周线" value="1w" />
        <el-option label="月线" value="1M" />
      </el-select>

      <el-select
        v-model="subIndicators"
        multiple
        collapse-tags
        collapse-tags-tooltip
        :max-collapse-tags="2"
        size="default"
        class="indicator-select"
        placeholder="副图指标"
        @change="handleSubChange"
      >
        <el-option label="成交量 VOL" value="VOL" />
        <el-option label="MACD" value="MACD" />
        <el-option label="BOLL" value="BOLL" />
        <el-option label="RSI" value="RSI" />
        <el-option label="KDJ" value="KDJ" />
      </el-select>

      <span class="topbar__spacer" />

      <!-- 图例提示 — design.md D9 图例 -->
      <div class="tip legend-trigger">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" />
        </svg>
        <div class="tip__bubble">
          <div class="legend-title">缠论图例</div>
          <div class="legend-row"><span class="sw"></span>笔（灰线）</div>
          <div class="legend-row"><span class="sw sw--seg"></span>线段（蓝线）</div>
          <div class="legend-row"><span class="sw sw--box"></span>笔中枢（灰框）</div>
          <div class="legend-row"><span class="sw sw--box sw--box2"></span>线段中枢（蓝框）</div>
          <div class="legend-row"><span class="dot dot--buy"></span>买点（1B/2B/L2B/3B）</div>
          <div class="legend-row"><span class="dot dot--sell"></span>卖点（1S/2S/L2S/3S）</div>
        </div>
      </div>
    </header>

    <!-- 主图区 — design.md D9 -->
    <section class="chart chart--grid main-chart reveal reveal--1">
      <div class="chart__tag">{{ code.toUpperCase() }} · {{ periodLabel }} · 前复权</div>
      <KLineChart ref="chartComp" :result="result" />
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * KLineView.vue — K 线分析页
 * design.md D9：topbar + main-chart + subchart×N
 * design.md D6：切换代码/周期触发命令式重载
 */
import { ref, computed, onMounted, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import KLineChart from '@/components/charts/KLineChart.vue'
import { getKLine } from '@/api/modules/kline'
import type { ChanResult } from '@/api/types'

const SearchIcon = Search

const codeInput = ref('sz.000001')
const code = ref('sz.000001')
const period = ref('1d')
const loading = ref(false)
const result = ref<ChanResult | null>(null)
const subIndicators = ref<string[]>(['VOL', 'MACD'])

const chartComp = ref<InstanceType<typeof KLineChart> | null>(null)

const periodLabel = computed(() => {
  const m: Record<string, string> = {
    '1m': '1分钟', '5m': '5分钟', '1h': '1小时', '1d': '日线', '1w': '周线', '1M': '月线',
  }
  return m[period.value] ?? period.value
})

/** 加载 K 线 + 缠论数据 */
async function load(): Promise<void> {
  loading.value = true
  try {
    const res = await getKLine(code.value)
    result.value = res
  } catch (e) {
    ElMessage.error('加载 K 线数据失败')
    result.value = null
  } finally {
    loading.value = false
  }
}

/** 搜索 — 切换代码/周期触发重载 */
function handleSearch(): void {
  const c = codeInput.value.trim()
  if (!c) {
    ElMessage.warning('请输入股票代码')
    return
  }
  code.value = c
  load()
}

/** 副图指标增删 */
function handleSubChange(): void {
  if (subIndicators.value.length > 5) {
    ElMessage.warning('副图指标最多 5 个')
    subIndicators.value = subIndicators.value.slice(0, 5)
    return
  }
  chartComp.value?.syncSubIndicators(subIndicators.value)
}

onMounted(() => {
  load()
})

// 周期切换触发重载
watch(period, () => load())

// 数据加载后同步副图指标
watch(result, () => {
  if (result.value) {
    chartComp.value?.syncSubIndicators(subIndicators.value)
  }
})
</script>

<style scoped>
.kline-page {
  display: flex;
  flex-direction: column;
  /* AppShell content 区有 topnav(52px) + content padding(24px*2)，填满剩余视口 */
  height: calc(100vh - var(--topnav-h) - var(--sp-2xl) * 2);
  min-height: 520px;
  gap: var(--sp-sm);
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--sp-md);
  height: var(--topbar-h);
  padding: 0 var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
  background: var(--bg-surface);
  flex-shrink: 0;
  position: relative;
  z-index: 20;
}
.topbar .topbar__spacer { flex: 1; }

.code-field {
  width: 220px;
}
.code-field :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  box-shadow: 0 0 0 1px var(--border-base) inset;
}
.code-field :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--accent-base) inset, 0 0 14px var(--accent-glow);
}
.code-field :deep(.el-input__inner) {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
}

.period-select {
  width: 110px;
}
.indicator-select {
  width: 200px;
}
.period-select :deep(.el-select__wrapper),
.indicator-select :deep(.el-select__wrapper) {
  background: var(--bg-surface);
  box-shadow: 0 0 0 1px var(--border-base) inset;
}
.period-select :deep(.el-select__wrapper.is-focused),
.indicator-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--accent-base) inset, 0 0 14px var(--accent-glow);
}

/* 图例 */
.legend-trigger {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--r-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-left: auto;
}
.legend-trigger:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 3px 0;
}
.legend-row .sw {
  width: 16px;
  height: 0;
  border-top: 2px solid var(--text-secondary);
}
.legend-row .sw--seg {
  border-color: var(--accent-base);
  border-top-width: 3px;
}
.legend-row .sw--box {
  width: 16px;
  height: 9px;
  border: 1px dashed var(--text-secondary);
  border-top: none;
  border-radius: 1px;
}
.legend-row .sw--box2 {
  border-color: var(--accent-base);
  border-style: solid;
  background: rgba(59, 130, 246, 0.12);
}
.legend-row .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.legend-row .dot--buy { background: var(--rise); }
.legend-row .dot--sell { background: var(--fall); }
.legend-title {
  font-size: 11px;
  color: var(--text-disabled);
  letter-spacing: 0.08em;
  margin-bottom: 4px;
}

/* 主图区 */
.main-chart {
  flex: 1;
  min-height: 320px;
  position: relative;
  overflow: hidden;
}
.chart__tag {
  position: absolute;
  top: 10px;
  left: 14px;
  font-size: 11px;
  color: var(--text-disabled);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
  pointer-events: none;
  z-index: 5;
}
</style>
