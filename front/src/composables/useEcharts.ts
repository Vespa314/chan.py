import { ref, onMounted, onBeforeUnmount, type Ref } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

/**
 * ECharts composable — 实例非响应式（design.md D6 同款策略）
 * chart 实例不进 ref 的 reactive 包装，用 shallowRef 或 let 变量。
 */
export function useEcharts(el: Ref<HTMLElement | null>) {
  let chart: echarts.ECharts | null = null

  function init() {
    if (!el.value) return
    chart = echarts.init(el.value, undefined, { renderer: 'canvas' })
    return chart
  }

  function setOption(option: echarts.EChartsCoreOption) {
    if (!chart) init()
    chart?.setOption(option, true)
  }

  function resize() {
    chart?.resize()
  }

  function dispose() {
    chart?.dispose()
    chart = null
  }

  onMounted(() => {
    init()
    window.addEventListener('resize', resize)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    dispose()
  })

  return { setOption, resize, dispose, getChart: () => chart }
}
