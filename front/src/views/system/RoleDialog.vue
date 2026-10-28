<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑角色' : '新建角色'"
    width="520px"
    :close-on-click-modal="false"
    append-to-body
    class="role-dialog"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSave">
      <el-form-item label="角色名" prop="name">
        <el-input v-model="form.name" placeholder="如：交易员" />
      </el-form-item>
      <el-form-item label="角色代码" prop="code">
        <el-input v-model="form.code" placeholder="如：trader" :disabled="isEdit && isAdminRole" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="角色描述" />
      </el-form-item>
      <el-form-item label="权限配置" prop="perms">
        <div class="perm-box">
          <div class="perm-group">
            <div class="perm-group__title">
              <el-checkbox
                :model-value="isAllMenu"
                :indeterminate="isSomeMenu"
                @change="toggleAllMenu"
              >
                菜单权限 <span class="perm-code mono">menu:*</span>
              </el-checkbox>
            </div>
            <el-checkbox-group v-model="form.perms" class="perm-children">
              <el-checkbox
                v-for="p in menuPerms"
                :key="p.code"
                :value="p.code"
              >
                {{ p.name }} <span class="perm-code mono">{{ p.code }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </div>
          <div class="perm-group">
            <div class="perm-group__title">
              <el-checkbox
                :model-value="form.perms.includes('manage')"
                @change="toggleManage"
              >
                管理权限 <span class="perm-code mono">manage</span>
              </el-checkbox>
            </div>
          </div>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="isAdminRole" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { Role, Permission } from '@/api/types'
import * as systemApi from '@/api/modules/system'

const props = defineProps<{
  modelValue: boolean
  role: Role | null
  permissions: Permission[]
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const isEdit = computed(() => !!props.role)
const isAdminRole = computed(() => props.role?.code === 'admin')

const menuPerms = computed(() => props.permissions.filter((p) => p.category === '菜单'))
const menuCodes = computed(() => menuPerms.value.map((p) => p.code))

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  name: '',
  code: '',
  description: '',
  perms: [] as string[],
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入角色名', trigger: 'blur' }],
  code: [{ required: true, message: '请输入角色代码', trigger: 'blur' }],
}

const isAllMenu = computed(() =>
  menuCodes.value.every((c) => form.perms.includes(c)),
)
const isSomeMenu = computed(
  () => !isAllMenu.value && menuCodes.value.some((c) => form.perms.includes(c)),
)

function toggleAllMenu(v: boolean | string | number) {
  const checked = Boolean(v)
  if (checked) {
    const set = new Set(form.perms)
    menuCodes.value.forEach((c) => set.add(c))
    form.perms = [...set]
  } else {
    form.perms = form.perms.filter((c) => !menuCodes.value.includes(c))
  }
}

function toggleManage(v: boolean | string | number) {
  const checked = Boolean(v)
  const set = new Set(form.perms)
  if (checked) set.add('manage')
  else set.delete('manage')
  form.perms = [...set]
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.role) {
      Object.assign(form, {
        name: props.role.name,
        code: props.role.code,
        description: props.role.description,
        perms: [...props.role.perms],
      })
    } else {
      Object.assign(form, {
        name: '',
        code: '',
        description: '',
        perms: [],
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
      if (props.role) {
        await systemApi.updateRole(props.role.id, {
          name: form.name,
          description: form.description,
          perms: form.perms,
        })
        ElMessage.success('角色已更新')
      } else {
        await systemApi.createRole({
          name: form.name,
          code: form.code,
          description: form.description,
          perms: form.perms,
        })
        ElMessage.success('角色已创建')
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

<style scoped>
.perm-box {
  display: flex;
  flex-direction: column;
  gap: var(--sp-md);
  width: 100%;
}
.perm-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.perm-group__title {
  font-weight: 600;
  font-size: 13px;
}
.perm-children {
  margin-left: 26px;
  padding-left: 8px;
  border-left: 1px solid var(--border-base);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.perm-children :deep(.el-checkbox) {
  height: 28px;
}
.perm-code {
  font-size: 11px;
  color: var(--text-disabled);
  margin-left: 2px;
}
</style>
