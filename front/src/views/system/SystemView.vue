<template>
  <div class="system-page">
    <div class="panel">
      <el-tabs v-model="activeTab" class="system-tabs">
        <!-- 用户管理 -->
        <el-tab-pane label="用户管理" name="users">
          <div class="toolbar">
            <span class="spacer"></span>
            <el-button v-permission="'manage'" type="primary" size="small" :icon="Plus" @click="openUserCreate">
              新建用户
            </el-button>
          </div>

          <el-table
            v-loading="usersLoading"
            :data="users"
            stripe
            empty-text="暂无用户"
            style="width: 100%"
          >
            <el-table-column label="用户名" prop="username" width="140" class-name="mono-col" />
            <el-table-column label="昵称" prop="nickname" min-width="120" />
            <el-table-column label="角色" width="120">
              <template #default="{ row }">
                <span class="badge" :class="row.role === 'admin' ? 'badge--accent' : 'badge--default'">
                  {{ row.role_name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch
                  v-model="row.status"
                  active-value="active"
                  inactive-value="disabled"
                  :disabled="row.role === 'admin'"
                  @change="(v: string) => onToggleUser(row, v as 'active' | 'disabled')"
                />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="120">
              <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="最后登录" width="140">
              <template #default="{ row }">
                <span v-if="row.last_login">{{ fmtDateTime(row.last_login) }}</span>
                <span v-else class="text-disabled">—</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" align="right">
              <template #default="{ row }">
                <el-button v-permission="'manage'" link type="primary" size="small" @click="openUserEdit(row)">编辑</el-button>
                <el-button v-permission="'manage'" link type="primary" size="small" @click="onResetPwd(row)">重置密码</el-button>
                <el-button
                  v-permission="'manage'"
                  link
                  type="danger"
                  size="small"
                  :disabled="row.role === 'admin'"
                  @click="onDeleteUser(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 角色管理 -->
        <el-tab-pane label="角色管理" name="roles">
          <div class="toolbar">
            <span class="spacer"></span>
            <el-button v-permission="'manage'" type="primary" size="small" :icon="Plus" @click="openRoleCreate">
              新建角色
            </el-button>
          </div>

          <el-table
            v-loading="rolesLoading"
            :data="roles"
            stripe
            empty-text="暂无角色"
            style="width: 100%"
          >
            <el-table-column label="角色名" prop="name" min-width="140" />
            <el-table-column label="角色代码" prop="code" width="140" class-name="mono-col" />
            <el-table-column label="描述" prop="description" min-width="200" />
            <el-table-column label="用户数" prop="user_count" width="90" align="right" class-name="mono-col" />
            <el-table-column label="是否 admin" width="130">
              <template #default="{ row }">
                <span v-if="row.code === 'admin'" class="badge badge--warning">是 · 内置</span>
                <span v-else class="badge badge--default">否</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="right">
              <template #default="{ row }">
                <el-button v-permission="'manage'" link type="primary" size="small" @click="openRoleEdit(row)">编辑</el-button>
                <el-button
                  v-permission="'manage'"
                  link
                  type="danger"
                  size="small"
                  :disabled="row.code === 'admin'"
                  @click="onDeleteRole(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 权限配置 -->
        <el-tab-pane label="权限配置" name="perm">
          <div class="perm-config">
            <div class="form-row">
              <label>选择角色</label>
              <el-select v-model="permRoleCode" placeholder="选择角色" style="width: 240px" @change="onPermRoleChange">
                <el-option
                  v-for="r in roles"
                  :key="r.code"
                  :label="r.name"
                  :value="r.code"
                />
              </el-select>
            </div>

            <div v-if="permRole" class="perm-tree">
              <div class="perm-group">
                <div class="perm-node perm-node--parent">
                  <el-checkbox
                    :model-value="isAllMenu"
                    :indeterminate="isSomeMenu"
                    :disabled="permRole.code === 'admin'"
                    @change="toggleAllMenu"
                  >
                    菜单权限 <span class="perm-code mono">menu:*</span>
                  </el-checkbox>
                </div>
                <div class="perm-children">
                  <div v-for="p in menuPerms" :key="p.code" class="perm-node">
                    <el-checkbox
                      :model-value="permDraft.includes(p.code)"
                      :disabled="permRole.code === 'admin'"
                      @change="(v: boolean | string | number) => togglePerm(p.code, v)"
                    >
                      {{ p.name }} <span class="perm-code mono">{{ p.code }}</span>
                    </el-checkbox>
                  </div>
                </div>
              </div>
              <div class="perm-group">
                <div class="perm-node perm-node--parent">
                  <el-checkbox
                    :model-value="permDraft.includes('manage')"
                    :disabled="permRole.code === 'admin'"
                    @change="(v: boolean | string | number) => togglePerm('manage', v)"
                  >
                    管理权限 <span class="perm-code mono">manage</span>
                  </el-checkbox>
                </div>
              </div>

              <div class="toolbar">
                <el-button
                  v-permission="'manage'"
                  type="primary"
                  :loading="permSaving"
                  :disabled="permRole.code === 'admin'"
                  @click="onSavePerms"
                >
                  保存
                </el-button>
                <span v-if="permRole.code === 'admin'" class="text-disabled admin-hint">admin 角色拥有全部权限，不可修改</span>
              </div>
            </div>

            <EmptyState v-else description="请选择角色以配置权限" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <UserDialog v-model="userDialogVisible" :user="editingUser" :roles="roles" @saved="loadUsers" />
    <RoleDialog v-model="roleDialogVisible" :role="editingRole" :permissions="permissions" @saved="loadRoles" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import EmptyState from '@/components/ui/EmptyState.vue'
import UserDialog from './UserDialog.vue'
import RoleDialog from './RoleDialog.vue'
import * as systemApi from '@/api/modules/system'
import type { User, Role, Permission } from '@/api/types'

const activeTab = ref<'users' | 'roles' | 'perm'>('users')

const users = ref<User[]>([])
const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const usersLoading = ref(false)
const rolesLoading = ref(false)

async function loadUsers() {
  usersLoading.value = true
  try {
    users.value = await systemApi.getUsers()
  } catch {
    // handled
  } finally {
    usersLoading.value = false
  }
}

async function loadRoles() {
  rolesLoading.value = true
  try {
    roles.value = await systemApi.getRoles()
  } catch {
    // handled
  } finally {
    rolesLoading.value = false
  }
}

async function loadPermissions() {
  try {
    permissions.value = await systemApi.getPermissions()
  } catch {
    // handled
  }
}

onMounted(() => {
  loadUsers()
  loadRoles()
  loadPermissions()
})

// --- 用户操作 ---
const userDialogVisible = ref(false)
const editingUser = ref<User | null>(null)

function openUserCreate() {
  editingUser.value = null
  userDialogVisible.value = true
}
function openUserEdit(row: User) {
  editingUser.value = { ...row }
  userDialogVisible.value = true
}

async function onToggleUser(row: User, v: 'active' | 'disabled') {
  try {
    await systemApi.updateUser(row.id, { status: v })
    ElMessage.success(v === 'active' ? '已启用' : '已禁用')
  } catch {
    row.status = v === 'active' ? 'disabled' : 'active'
  }
}

async function onResetPwd(row: User) {
  try {
    await ElMessageBox.confirm(`确定重置用户「${row.username}」的密码？`, '重置密码', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await systemApi.resetPassword(row.id)
    ElMessage.success('密码已重置')
  } catch {
    // handled
  }
}

async function onDeleteUser(row: User) {
  if (row.role === 'admin') {
    ElMessage.warning('管理员不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await systemApi.deleteUser(row.id)
    ElMessage.success('已删除')
    loadUsers()
  } catch {
    // handled
  }
}

// --- 角色操作 ---
const roleDialogVisible = ref(false)
const editingRole = ref<Role | null>(null)

function openRoleCreate() {
  editingRole.value = null
  roleDialogVisible.value = true
}
function openRoleEdit(row: Role) {
  editingRole.value = { ...row }
  roleDialogVisible.value = true
}

async function onDeleteRole(row: Role) {
  if (row.code === 'admin') {
    ElMessage.warning('管理员角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await systemApi.deleteRole(row.id)
    ElMessage.success('已删除')
    loadRoles()
  } catch {
    // handled
  }
}

// --- 权限配置 ---
const permRoleCode = ref('')
const permDraft = ref<string[]>([])
const permSaving = ref(false)

const permRole = computed(() => roles.value.find((r) => r.code === permRoleCode.value) || null)
const menuPerms = computed(() => permissions.value.filter((p) => p.category === '菜单'))
const menuCodes = computed(() => menuPerms.value.map((p) => p.code))
const isAllMenu = computed(() =>
  menuCodes.value.length > 0 && menuCodes.value.every((c) => permDraft.value.includes(c)),
)
const isSomeMenu = computed(
  () => !isAllMenu.value && menuCodes.value.some((c) => permDraft.value.includes(c)),
)

function onPermRoleChange(code: string) {
  const r = roles.value.find((x) => x.code === code)
  permDraft.value = r ? [...r.perms] : []
}

function toggleAllMenu(v: boolean | string | number) {
  if (permRole.value?.code === 'admin') return
  const checked = Boolean(v)
  const set = new Set(permDraft.value)
  if (checked) menuCodes.value.forEach((c) => set.add(c))
  else menuCodes.value.forEach((c) => set.delete(c))
  permDraft.value = [...set]
}

function togglePerm(code: string, v: boolean | string | number) {
  if (permRole.value?.code === 'admin') return
  const checked = Boolean(v)
  const set = new Set(permDraft.value)
  if (checked) set.add(code)
  else set.delete(code)
  permDraft.value = [...set]
}

async function onSavePerms() {
  if (!permRole.value) return
  permSaving.value = true
  try {
    await systemApi.updateRole(permRole.value.id, { perms: permDraft.value })
    ElMessage.success('权限已保存')
    loadRoles()
  } catch {
    // handled
  } finally {
    permSaving.value = false
  }
}

// --- 辅助 ---
function fmtDate(ts: number) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function fmtDateTime(ts: number) {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.system-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
  flex: 1;
}

.system-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 var(--sp-lg);
  border-bottom: 1px solid var(--border-base);
}
.system-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.system-tabs :deep(.el-tab-pane) {
  padding: 0 var(--sp-lg) var(--sp-lg);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--sp-sm);
  padding: var(--sp-md) 0;
}
.toolbar .spacer {
  flex: 1;
}

.mono-col {
  font-family: var(--font-mono);
}

.text-disabled {
  color: var(--text-disabled);
}

/* 权限配置 */
.perm-config {
  padding: var(--sp-sm) 0;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: var(--sp-md);
}
.form-row label {
  font-size: 13px;
  color: var(--text-secondary);
}

.perm-tree {
  display: flex;
  flex-direction: column;
  gap: var(--sp-md);
  max-width: 560px;
}
.perm-group {
  display: flex;
  flex-direction: column;
}
.perm-node {
  height: 36px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  border-radius: var(--r-sm);
  font-size: 13px;
}
.perm-node:hover {
  background: var(--bg-surface-hover);
}
.perm-node--parent {
  font-weight: 600;
}
.perm-children {
  margin-left: 26px;
  padding-left: 8px;
  border-left: 1px solid var(--border-base);
  display: flex;
  flex-direction: column;
}
.perm-code {
  font-size: 11px;
  color: var(--text-disabled);
  margin-left: 2px;
}
.admin-hint {
  font-size: 12px;
  margin-left: var(--sp-sm);
}
</style>
