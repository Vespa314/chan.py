<template>
  <div ref="el" class="profit-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useEcharts } from '@/composables/useEcharts'

interface SeriesPoint {
  date: string
  value: number
}

const props = defineProps<{
  series: SeriesPoint[]
}>()

const el = ref<HTMLElement | null>(null)
const { setOption } = useEcharts(el)

function render() {
  if (!props.series || props.series.length === 0) return
  setOption({
    backgroundColor: 'transparent',
    grid: { left: 48, right: 20, top: 20, bottom: 32 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161B22',
      borderColor: '#2A303A',
      textStyle: { color: '#E6E8EB', fontSize: 12 },
      valueFormatter: (v: number) => `+${v.toFixed(2)}%`,
    },
    xAxis: {
      type: 'category',
      data: props.series.map((p) => p.date),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#2A303A' } },
      axisLabel: { color: '#565D66', fontSize: 11, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: 'rgba(42,48,58,0.5)', type: 'dashed' } },
      axisLabel: {
        color: '#565D66',
        fontSize: 11,
        fontFamily: 'JetBrains Mono',
        formatter: '{value}%',
      },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        data: props.series.map((p) => p.value),
        lineStyle: { color: '#F6465D', width: 2.2 },
        itemStyle: { color: '#F6465D', borderColor: '#0A0D12', borderWidth: 2 },
        emphasis: { focus: 'series' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(246,70,93,0.22)' },
              { offset: 1, color: 'rgba(246,70,93,0)' },
            ],
          },
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#3A424E', type: 'dashed' },
          data: [{ yAxis: 0 }],
        },
      },
    ],
  })
}

onMounted(render)
watch(() => props.series, render, { deep: true })
</script>

<style scoped>
.profit-chart {
  height: 280px;
  width: 100%;
}
</style>
