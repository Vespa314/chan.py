<template>
  <el-drawer
    v-model="visible"
    title="归因详情"
    direction="rtl"
    size="480px"
    :before-close="handleClose"
  >
    <template v-if="item">
      <div class="attr-section">
        <span class="attr-label">标的</span>
        <div class="cell-stock">
          <span class="nm">{{ item.name }}</span>
          <span class="cd mono">{{ item.code }}</span>
        </div>
      </div>

      <div class="attr-section">
        <span class="attr-label">失败原因分类</span>
        <div>
          <span class="badge" :class="reasonBadgeClass">{{ reasonCategory }}</span>
        </div>
      </div>

      <div class="attr-section">
        <span class="attr-label">证据</span>
        <div class="attr-box">{{ item.attribution }}</div>
      </div>

      <div class="attr-section">
        <span class="attr-label">输入摘要</span>
        <div class="attr-box">
          标的 {{ item.code }} {{ item.name }} · {{ klTypeLabel }} · 买入价
          {{ item.bsp_price }} · 卖出价 {{ item.end_price }}
        </div>
      </div>

      <div class="attr-section">
        <span class="attr-label">盈亏</span>
        <div>
          <span class="num" :class="item.profit >= 0 ? 'text-rise' : 'text-fall'" style="font-size:16px;font-weight:600">
            {{ item.profit >= 0 ? '+' : '' }}{{ item.profit.toFixed(2) }}%
          </span>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CompletedItem } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  item: CompletedItem | null
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'reanalyze': [id: number]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const klTypeLabel = computed(() => {
  if (!props.item) return ''
  const m: Record<string, string> = { D: '日线', '60m': '60分钟', '30m': '30分钟', '15m': '15分钟' }
  return m[props.item.kl_type] || props.item.kl_type
})

/** 简单归因分类：根据 attribution 文本关键词推断 */
const reasonCategory = computed(() => {
  if (!props.item) return '未归因'
  const t = props.item.attribution || ''
  if (/包含|逻辑|计算|中枢区间|端点/.test(t)) return '计算逻辑错误'
  return '缠论失效'
})

const reasonBadgeClass = computed(() => {
  return reasonCategory.value === '计算逻辑错误' ? 'badge--info' : 'badge--warning'
})

function handleClose(done: () => void) {
  done()
}
</script>

<style scoped>
.attr-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 20px;
}
.attr-label {
  font-size: 12px;
  color: var(--text-secondary);
}
.attr-box {
  background: var(--bg-surface);
  border: 1px solid var(--border-base);
  border-radius: var(--r-md);
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
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
