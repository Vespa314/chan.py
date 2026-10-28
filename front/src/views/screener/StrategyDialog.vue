<template>
  <el-dialog
    v-model="visibleRef"
    :title="isEdit ? '编辑策略' : '新建策略'"
    width="560px"
    append-to-body
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="策略名" prop="name">
        <el-input v-model="form.name" placeholder="如：日线一买突破" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="2"
          placeholder="策略描述"
        />
      </el-form-item>
      <el-form-item label="买卖点类型" prop="bsp_types">
        <el-select
          v-model="form.bsp_types"
          multiple
          placeholder="选择买卖点类型"
          style="width: 100%"
        >
          <el-option v-for="t in ALL_BSP_LABELS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="级别" prop="kl_type">
        <el-select v-model="form.kl_type" placeholder="选择级别" style="width: 100%">
          <el-option v-for="kl in klOptions" :key="kl.value" :label="kl.label" :value="kl.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="行业" prop="industries">
        <el-select
          v-model="form.industries"
          multiple
          filterable
          placeholder="不限"
          style="width: 100%"
        >
          <el-option v-for="ind in allIndustries" :key="ind" :label="ind" :value="ind" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-switch
          v-model="form.status"
          active-value="active"
          inactive-value="inactive"
          active-text="启用"
          inactive-text="停用"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visibleRef = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存策略</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createStrategy, updateStrategy } from '@/api/modules/screener'
import { ALL_BSP_LABELS } from '@/utils/bsp'
import { allIndustries } from '@/mock/data/stocks'
import type { Strategy } from '@/api/types'

const props = defineProps<{
  visible: boolean
  strategy: Strategy | null
}>()
const emit = defineEmits<{
  'update:visible': [v: boolean]
  saved: []
}>()

const visibleRef = ref(props.visible)
watch(() => props.visible, (v) => (visibleRef.value = v))
watch(visibleRef, (v) => emit('update:visible', v))

const isEdit = computed(() => !!props.strategy)

const klOptions = [
  { label: '日线', value: 'D' },
  { label: '60分钟', value: '60m' },
  { label: '30分钟', value: '30m' },
  { label: '周线', value: 'W' },
]

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  name: '',
  description: '',
  bsp_types: [] as string[],
  kl_type: 'D',
  industries: [] as string[],
  status: 'active' as 'active' | 'inactive',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入策略名', trigger: 'blur' }],
  bsp_types: [{ required: true, message: '请选择买卖点类型', trigger: 'change' }],
  kl_type: [{ required: true, message: '请选择级别', trigger: 'change' }],
}

// 初始化表单
watch(
  () => props.visible,
  (v) => {
    if (!v) return
    if (props.strategy) {
      Object.assign(form, {
        name: props.strategy.name,
        description: props.strategy.description,
        bsp_types: [...props.strategy.bsp_types],
        kl_type: props.strategy.kl_type,
        industries: [...props.strategy.industries],
        status: props.strategy.status,
      })
    } else {
      Object.assign(form, {
        name: '',
        description: '',
        bsp_types: [],
        kl_type: 'D',
        industries: [],
        status: 'active',
      })
    }
  },
  { immediate: true },
)

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const data: Omit<Strategy, 'id'> = {
        name: form.name,
        description: form.description,
        bsp_types: form.bsp_types,
        kl_type: form.kl_type,
        industries: form.industries,
        status: form.status,
      }
      if (isEdit.value && props.strategy) {
        await updateStrategy(props.strategy.id, data)
        ElMessage.success('策略已更新')
      } else {
        await createStrategy(data)
        ElMessage.success('策略已创建')
      }
      emit('saved')
    } catch {
      // 失败已由拦截器处理
    } finally {
      saving.value = false
    }
  })
}
</script>
