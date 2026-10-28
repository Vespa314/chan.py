<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑规则' : '新建规则'"
    width="480px"
    :close-on-click-modal="false"
    append-to-body
    class="rule-dialog"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSave">
      <el-form-item label="规则名" prop="name">
        <el-input v-model="form.name" placeholder="如：平安银行一买提醒" />
      </el-form-item>
      <el-form-item label="目标股票" prop="code">
        <el-select
          v-model="form.code"
          filterable
          remote
          :remote-method="onSearch"
          placeholder="输入代码或名称搜索"
          style="width: 100%"
          @change="onStockChange"
        >
          <el-option
            v-for="s in options"
            :key="s.code"
            :label="`${s.name} · ${s.code}`"
            :value="s.code"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="条件" prop="condition">
        <el-input v-model="form.condition" placeholder="如：出现1B买点 / 价格 ≥ 10.50" />
      </el-form-item>
      <el-form-item label="级别" prop="kl_type">
        <el-select v-model="form.kl_type" placeholder="选择级别" style="width: 100%">
          <el-option label="日线" value="D" />
          <el-option label="60分钟" value="60m" />
          <el-option label="30分钟" value="30m" />
          <el-option label="5分钟" value="5m" />
        </el-select>
      </el-form-item>
      <el-form-item label="启用状态">
        <el-switch v-model="form.enabled" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存规则</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { stocks as allStocks } from '@/mock/data/stocks'
import type { AlertRule, Stock } from '@/api/types'
import * as alertsApi from '@/api/modules/alerts'

const props = defineProps<{
  modelValue: boolean
  rule: AlertRule | null
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.rule)
const formRef = ref<FormInstance>()
const saving = ref(false)
const options = ref<Stock[]>([...allStocks])

const form = reactive({
  name: '',
  code: '',
  stock_name: '',
  condition: '',
  kl_type: 'D',
  enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入规则名', trigger: 'blur' }],
  code: [{ required: true, message: '请选择目标股票', trigger: 'change' }],
  condition: [{ required: true, message: '请输入条件', trigger: 'blur' }],
  kl_type: [{ required: true, message: '请选择级别', trigger: 'change' }],
}

function onSearch(query: string) {
  if (!query) {
    options.value = [...allStocks]
    return
  }
  const q = query.toLowerCase()
  options.value = allStocks.filter(
    (s) => s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q),
  )
}

function onStockChange(code: string) {
  const s = allStocks.find((x) => x.code === code)
  if (s) form.stock_name = s.name
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.rule) {
      Object.assign(form, {
        name: props.rule.name,
        code: props.rule.code,
        stock_name: props.rule.stock_name,
        condition: props.rule.condition,
        kl_type: props.rule.kl_type,
        enabled: props.rule.enabled,
      })
    } else {
      Object.assign(form, {
        name: '',
        code: '',
        stock_name: '',
        condition: '',
        kl_type: 'D',
        enabled: true,
      })
    }
    options.value = [...allStocks]
  },
)

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: form.name,
        code: form.code,
        stock_name: form.stock_name || allStocks.find((s) => s.code === form.code)?.name || '',
        condition: form.condition,
        kl_type: form.kl_type,
        enabled: form.enabled,
      }
      if (props.rule) {
        await alertsApi.updateRule(props.rule.id, payload)
        ElMessage.success('规则已更新')
      } else {
        await alertsApi.createRule(payload)
        ElMessage.success('规则已创建')
      }
      visible.value = false
      emit('saved')
    } catch {
      // 错误已由拦截器处理
    } finally {
      saving.value = false
    }
  })
}
</script>

<style scoped>
.rule-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}
</style>
