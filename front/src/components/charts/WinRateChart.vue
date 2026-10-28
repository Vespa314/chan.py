<template>
  <div ref="el" class="winrate-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useEcharts } from '@/composables/useEcharts'

interface BarItem {
  name: string
  winRate: number
}

const props = defineProps<{
  data: BarItem[]
}>()

const el = ref<HTMLElement | null>(null)
const { setOption } = useEcharts(el)

function render() {
  if (!props.data || props.data.length === 0) return
  setOption({
    backgroundColor: 'transparent',
    grid: { left: 48, right: 20, top: 24, bottom: 32 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161B22',
      borderColor: '#2A303A',
      textStyle: { color: '#E6E8EB', fontSize: 12 },
      axisPointer: { type: 'shadow' },
      valueFormatter: (v: number) => `${v}%`,
    },
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.name),
      axisLine: { lineStyle: { color: '#2A303A' } },
      axisLabel: { color: '#9BA1A8', fontSize: 12, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      max: 100,
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
        type: 'bar',
        barWidth: 38,
        data: props.data.map((d) => ({
          value: d.winRate,
          itemStyle: { color: d.winRate >= 50 ? '#F6465D' : '#2EBD85' },
        })),
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#F6465D', type: 'dashed', width: 1.5 },
          label: {
            formatter: '50%',
            color: '#F6465D',
            fontSize: 11,
            fontFamily: 'JetBrains Mono',
          },
          data: [{ yAxis: 50 }],
        },
      },
    ],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<style scoped>
.winrate-chart {
  height: 220px;
  width: 100%;
}
</style>
