<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑用户' : '新建用户'"
    width="480px"
    :close-on-click-modal="false"
    append-to-body
    class="user-dialog"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSave">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="登录用户名" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="显示名" prop="nickname">
        <el-input v-model="form.nickname" placeholder="显示名称" />
      </el-form-item>
      <el-form-item label="角色" prop="role">
        <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
          <el-option
            v-for="r in roles"
            :key="r.code"
            :label="r.name"
            :value="r.code"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-switch
          v-model="form.status"
          active-text="启用"
          inactive-text="禁用"
          active-value="active"
          inactive-value="disabled"
        />
      </el-form-item>
      <el-form-item v-if="!isEdit" label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="登录密码" />
      </el-form-item>
      <el-form-item v-else label="密码">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="留空则不修改密码"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { User, Role } from '@/api/types'
import * as systemApi from '@/api/modules/system'

const props = defineProps<{
  modelValue: boolean
  user: User | null
  roles: Role[]
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const isEdit = computed(() => !!props.user)

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  username: '',
  nickname: '',
  role: '',
  status: 'active' as 'active' | 'disabled',
  password: '',
})

const rules = computed<FormRules>(() => ({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  password: props.user
    ? []
    : [{ required: true, message: '请输入密码', trigger: 'blur' }],
}))

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.user) {
      Object.assign(form, {
        username: props.user.username,
        nickname: props.user.nickname,
        role: props.user.role,
        status: props.user.status,
        password: '',
      })
    } else {
      Object.assign(form, {
        username: '',
        nickname: '',
        role: props.roles[0]?.code || '',
        status: 'active',
        password: '',
      })
    }
  },
)

async function onSave() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const roleObj = props.roles.find((r) => r.code === form.role)
      if (props.user) {
        await systemApi.updateUser(props.user.id, {
          nickname: form.nickname,
          role: form.role,
          role_name: roleObj?.name || form.role,
          status: form.status,
        })
        ElMessage.success('用户已更新')
      } else {
        await systemApi.createUser({
          username: form.username,
          nickname: form.nickname,
          role: form.role,
          role_name: roleObj?.name || form.role,
          status: form.status,
        })
        ElMessage.success('用户已创建')
      }
      visible.value = false
      emit('saved')
    } catch {
      // handled
    } finally {
      saving.value = false
    }
  })
}
</script>
