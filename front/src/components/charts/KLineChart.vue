<template>
  <div class="kline-chart-wrap">
    <div ref="chartRef" class="kline-chart-el" />
    <div v-if="loading" class="kline-chart-loading">
      <span>加载中…</span>
    </div>
    <div v-else-if="empty" class="kline-chart-empty">
      <span>无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * KLineChart.vue — K 线 + 缠论 overlay 渲染
 * design.md D6：chart 实例非响应式，onMounted init，watch 命令式重载。
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import {
  init,
  dispose,
  type Chart,
  type KLineData,
  LineType,
  CandleType,
  TooltipShowRule,
  TooltipShowType,
} from 'klinecharts'
import type { ChanResult } from '@/api/types'
import { registerAllChanOverlays } from '@/components/chan'

const props = defineProps<{
  result: ChanResult | null
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const empty = ref(false)

// chart 实例非响应式（design.md D6）
let chart: Chart | null = null

/** 副图指标 pane id 前缀 */
const PANE_PREFIX = 'chan_sub_'
/** 当前已创建的副图指标 → paneId 映射 */
const subPaneMap = new Map<string, string>()

/** 红涨绿跌 — design.css --rise / --fall */
const UP_COLOR = '#F6465D'
const DOWN_COLOR = '#2EBD85'

/** 应用 K 线数据 + 缠论覆盖层 */
function applyResult(result: ChanResult): void {
  if (!chart) return

  const klines: KLineData[] = result.klines.map((k) => ({
    timestamp: k.timestamp,
    open: k.open,
    high: k.high,
    low: k.low,
    close: k.close,
    volume: k.volume,
  }))
  chart.applyNewData(klines)

  // 先移除旧覆盖层，再重建
  chart.removeOverlay('chan_bi')
  chart.removeOverlay('chan_seg')
  chart.removeOverlay('chan_zs')
  chart.removeOverlay('chan_bsp')

  // 笔覆盖层：points 按 [begin, end, begin, end, ...] 顺序
  if (result.bi.length > 0) {
    const biPoints: Array<{ timestamp: number; value: number }> = []
    for (const b of result.bi) {
      biPoints.push({ timestamp: b.begin.t, value: b.begin.v })
      biPoints.push({ timestamp: b.end.t, value: b.end.v })
    }
    chart.createOverlay({ name: 'chan_bi', points: biPoints })
  }

  // 线段覆盖层：同笔结构
  if (result.seg.length > 0) {
    const segPoints: Array<{ timestamp: number; value: number }> = []
    for (const s of result.seg) {
      segPoints.push({ timestamp: s.begin.t, value: s.begin.v })
      segPoints.push({ timestamp: s.end.t, value: s.end.v })
    }
    chart.createOverlay({ name: 'chan_seg', points: segPoints })
  }

  // 中枢覆盖层：每个中枢 4 个角点，extendData 存 meta
  const allZs = [
    ...result.zs.map((z) => ({ z, level: 'bi' as const })),
    ...result.seg_zs.map((z) => ({ z, level: 'seg' as const })),
  ]
  if (allZs.length > 0) {
    const zsPoints: Array<{ timestamp: number; value: number }> = []
    const zsMeta: Array<{ level: 'bi' | 'seg'; startIndex: number }> = []
    allZs.forEach(({ z, level }) => {
      const startIndex = zsPoints.length
      // 4 角：左上(begin,high) 右上(end,high) 右下(end,low) 左下(begin,low)
      zsPoints.push({ timestamp: z.begin_t, value: z.high })
      zsPoints.push({ timestamp: z.end_t, value: z.high })
      zsPoints.push({ timestamp: z.end_t, value: z.low })
      zsPoints.push({ timestamp: z.begin_t, value: z.low })
      zsMeta.push({ level, startIndex })
    })
    chart.createOverlay({
      name: 'chan_zs',
      points: zsPoints,
      extendData: zsMeta,
    })
  }

  // 买卖点覆盖层：每个买卖点 1 个点，extendData 存 meta
  if (result.bsp.length > 0) {
    const bspPoints: Array<{ timestamp: number; value: number }> = []
    const bspMeta: Array<{ isBuy: boolean; types: string[]; pointIndex: number }> = []
    result.bsp.forEach((b, i) => {
      bspPoints.push({ timestamp: b.t, value: b.v })
      bspMeta.push({ isBuy: b.is_buy, types: b.types, pointIndex: i })
    })
    chart.createOverlay({
      name: 'chan_bsp',
      points: bspPoints,
      extendData: bspMeta,
    })
  }
}

/** 初始化 chart 实例 */
function initChart(): void {
  if (!chartRef.value) return
  // 注册覆盖层（须在 init 之前）
  registerAllChanOverlays()
  chart = init(chartRef.value)
  if (!chart) return

  // 暗色主题 + 红涨绿跌
  chart.setStyles({
    grid: {
      horizontal: { show: true, color: 'rgba(42, 48, 58, 0.55)', style: LineType.Solid, size: 1, dashedValue: [2, 2] },
      vertical: { show: true, color: 'rgba(42, 48, 58, 0.55)', style: LineType.Solid, size: 1, dashedValue: [2, 2] },
    },
    candle: {
      type: CandleType.CandleSolid,
      bar: {
        upColor: UP_COLOR,
        downColor: DOWN_COLOR,
        noChangeColor: '#9BA1A8',
        upBorderColor: UP_COLOR,
        downBorderColor: DOWN_COLOR,
        noChangeBorderColor: '#9BA1A8',
        upWickColor: UP_COLOR,
        downWickColor: DOWN_COLOR,
        noChangeWickColor: '#9BA1A8',
      },
      priceMark: {
        show: true,
        high: { show: true, color: '#9BA1A8' },
        low: { show: true, color: '#9BA1A8' },
      },
      tooltip: {
        showRule: TooltipShowRule.Always,
        showType: TooltipShowType.Standard,
      },
    },
    xAxis: {
      show: true,
      axisLine: { show: true, color: '#2A303A', size: 1 },
      tickText: { show: true, color: '#565D66', size: 11 },
      tickLine: { show: true, color: '#2A303A', size: 1 },
    },
    yAxis: {
      show: true,
      axisLine: { show: true, color: '#2A303A', size: 1 },
      tickText: { show: true, color: '#565D66', size: 11 },
      tickLine: { show: true, color: '#2A303A', size: 1 },
    },
    crosshair: {
      show: true,
      horizontal: {
        show: true,
        line: { show: true, color: '#3B82F6', style: LineType.Dashed, size: 1, dashedValue: [4, 2] },
        text: { show: true, color: '#E6E8EB', backgroundColor: '#1C2128', size: 11, paddingLeft: 4, paddingRight: 4, paddingTop: 2, paddingBottom: 2, borderRadius: 2 },
      },
      vertical: {
        show: true,
        line: { show: true, color: '#3B82F6', style: LineType.Dashed, size: 1, dashedValue: [4, 2] },
        text: { show: true, color: '#E6E8EB', backgroundColor: '#1C2128', size: 11, paddingLeft: 4, paddingRight: 4, paddingTop: 2, paddingBottom: 2, borderRadius: 2 },
      },
    },
  })
}

/** 添加副图指标（VOL/MACD/BOLL/RSI/KDJ） */
function addSubIndicator(name: string): void {
  if (!chart) return
  if (subPaneMap.has(name)) return
  const paneId = `${PANE_PREFIX}${name.toLowerCase()}`
  chart.createIndicator(name, false, { id: paneId, height: 130 })
  subPaneMap.set(name, paneId)
}

/** 移除副图指标 */
function removeSubIndicator(name: string): void {
  if (!chart) return
  const paneId = subPaneMap.get(name)
  if (!paneId) return
  chart.removeIndicator(paneId)
  subPaneMap.delete(name)
}

/** 同步副图指标列表（增删） */
function syncSubIndicators(names: string[]): void {
  // 移除不在新列表中的
  for (const key of Array.from(subPaneMap.keys())) {
    if (!names.includes(key)) removeSubIndicator(key)
  }
  // 添加新出现的
  for (const name of names) {
    if (!subPaneMap.has(name)) addSubIndicator(name)
  }
}

onMounted(() => {
  initChart()
  if (props.result) {
    applyResult(props.result)
  }
})

watch(
  () => props.result,
  (result) => {
    if (!chart) return
    if (!result) {
      empty.value = true
      loading.value = false
      return
    }
    loading.value = false
    empty.value = result.klines.length === 0
    applyResult(result)
  },
)

onBeforeUnmount(() => {
  if (chart) {
    dispose(chart)
    chart = null
  }
})

defineExpose({
  resize: () => chart?.resize(),
  addSubIndicator,
  removeSubIndicator,
  syncSubIndicators,
})
</script>

<style scoped>
.kline-chart-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--bg-chart);
  border-radius: var(--r-md);
  overflow: hidden;
}
.kline-chart-el {
  width: 100%;
  height: 100%;
}
.kline-chart-loading,
.kline-chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-disabled);
  font-size: 13px;
  background: var(--bg-chart);
  z-index: 2;
}
</style>
