<template>
  <div class="watchlist-layout">
    <!-- 左侧文件夹树 -->
    <aside class="panel folder-panel reveal reveal--1">
      <div class="panel__head">
        自选
        <span class="spacer"></span>
        <button class="btn btn--ghost btn--sm" title="新建文件夹" @click="openCreateFolder">
          <span class="icon-plus"></span> 新建
        </button>
      </div>
      <div class="tree">
        <div
          class="tree__item"
          :class="{ 'is-active': activeKey === 'all' }"
          @click="selectFolder('all')"
        >
          <el-icon class="tree__icon"><Folder /></el-icon>
          <span>全部</span>
          <span class="count">{{ totalCount }}</span>
        </div>
        <div
          v-for="f in folders"
          :key="f.id"
          class="tree__item"
          :class="{ 'is-active': activeKey === String(f.id) }"
          @click="selectFolder(String(f.id))"
        >
          <el-icon class="tree__icon"><Folder /></el-icon>
          <span class="folder-name" :title="f.name">{{ f.name }}</span>
          <span class="count">{{ f.codes.length }}</span>
          <el-icon
            v-if="f.id !== 1"
            class="folder-del"
            title="删除文件夹"
            @click.stop="onDeleteFolder(f)"
          ><Close /></el-icon>
        </div>
      </div>
    </aside>

    <!-- 右侧主面板 -->
    <div class="main-panel">
      <!-- 工具条 -->
      <div class="toolbar reveal reveal--2">
        <div class="field" style="width: 240px">
          <el-icon class="field-icon"><Search /></el-icon>
          <input
            v-model="keyword"
            placeholder="搜索名称 / 编码"
            @input="onSearchInput"
          />
        </div>
        <span class="spacer"></span>
        <button class="btn btn--primary" @click="addDialogVisible = true">
          <span class="icon-plus"></span> 添加股票
        </button>
        <button class="btn btn--default" :disabled="!hasSelected" @click="onBatchRemove">
          批量移出
        </button>
      </div>

      <!-- 股票表格 -->
      <div class="panel reveal reveal--3" v-loading="loading">
        <div class="tbl-wrap">
          <el-table
            :data="pagedStocks"
            empty-text="该文件夹暂无股票"
            @selection-change="onSelectionChange"
            row-key="code"
          >
            <el-table-column type="selection" width="44" reserve-selection />
            <el-table-column label="名称 / 编码" width="200">
              <template #default="{ row }">
                <div class="cell-stock">
                  <span class="nm">{{ row.name }}</span>
                  <span class="cd mono">{{ row.code }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="股价" width="120" align="right" sortable :sort-by="'price'">
              <template #default="{ row }">
                <span class="num">{{ formatPrice(row.price) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="130" align="right" sortable :sort-by="'change_pct'">
              <template #default="{ row }">
                <ChangeBadge :value="row.change_pct" />
              </template>
            </el-table-column>
            <el-table-column label="行业" min-width="180">
              <template #default="{ row }">
                <IndustryBadges :industries="row.industries" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" align="right">
              <template #default="{ row }">
                <el-dropdown trigger="click" @command="(cmd: string) => onMove(row, cmd)">
                  <button class="row-action">移动</button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="f in folders"
                        :key="f.id"
                        :command="String(f.id)"
                        :disabled="currentFolderId === f.id"
                      >
                        {{ f.name }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <button class="row-action row-action--danger" @click="onRemove(row)">移出</button>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState description="该文件夹暂无股票，点击「添加股票」加入自选" />
            </template>
          </el-table>
        </div>

        <!-- 分页 -->
        <div class="pager" v-if="filteredStocks.length > 0">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="filteredStocks.length"
            :page-sizes="[20]"
            layout="total, prev, pager, next, jumper"
            background
          />
        </div>
      </div>
    </div>

    <!-- 新建文件夹弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建文件夹" width="420px" append-to-body>
      <el-form @submit.prevent>
        <el-form-item label="文件夹名">
          <el-input v-model="newFolderName" placeholder="请输入文件夹名" autofocus />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="onCreateFolder">确认</el-button>
      </template>
    </el-dialog>

    <!-- 添加股票弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加股票到自选" width="520px" append-to-body>
      <div class="add-dialog-body">
        <div class="form-row">
          <label>目标文件夹</label>
          <el-select v-model="addFolderId" placeholder="选择文件夹" style="width: 100%">
            <el-option v-for="f in folders" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </div>
        <div class="form-row">
          <label>股票编码</label>
          <el-select
            v-model="addStockCode"
            filterable
            remote
            :remote-method="searchStock"
            placeholder="输入名称或编码搜索"
            style="width: 100%"
            :loading="stockSearching"
          >
            <el-option
              v-for="s in stockOptions"
              :key="s.code"
              :label="`${s.name} (${s.code})`"
              :value="s.code"
            />
          </el-select>
        </div>
        <p class="dialog-hint">输入股票编码（如 sz.000001）从全市场搜索后添加到目标文件夹。</p>
      </div>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="onAddStock">确认加入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, Search, Close } from '@element-plus/icons-vue'
import { useDebounceFn } from '@vueuse/core'
import ChangeBadge from '@/components/ui/ChangeBadge.vue'
import IndustryBadges from '@/components/ui/IndustryBadges.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import {
  getFolders,
  createFolder,
  deleteFolder,
  getFolderStocks,
  addStock,
  removeStock,
  moveStock,
  type WatchFolder,
} from '@/api/modules/watchlist'
import { stocks as allStocks } from '@/mock/data/stocks'
import type { Stock } from '@/api/types'

// ---- 文件夹 ----
const folders = ref<WatchFolder[]>([])
const activeKey = ref<string>('all')
const loading = ref(false)

const currentFolderId = computed<number | null>(() => {
  if (activeKey.value === 'all') return null
  return Number(activeKey.value)
})

const totalCount = computed(() => {
  // 全部 = 去重后的股票数
  const set = new Set<string>()
  folders.value.forEach((f) => f.codes.forEach((c) => set.add(c)))
  return set.size
})

async function loadFolders() {
  loading.value = true
  try {
    folders.value = await getFolders()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function selectFolder(key: string) {
  activeKey.value = key
  page.value = 1
  clearSelection()
}

// ---- 股票列表（客户端分页，mock 返回全量） ----
const folderStocks = ref<Stock[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)

const filteredStocks = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return folderStocks.value
  return folderStocks.value.filter(
    (s) => s.code.toLowerCase().includes(kw) || s.name.toLowerCase().includes(kw),
  )
})

const pagedStocks = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredStocks.value.slice(start, start + pageSize.value)
})

async function loadStocks() {
  loading.value = true
  try {
    if (activeKey.value === 'all') {
      // 全部 = 跨文件夹去重
      const set = new Map<string, Stock>()
      for (const f of folders.value) {
        const list = await getFolderStocks(f.id)
        list.forEach((s) => {
          if (!set.has(s.code)) set.set(s.code, s)
        })
      }
      folderStocks.value = Array.from(set.values())
    } else {
      const id = Number(activeKey.value)
      folderStocks.value = await getFolderStocks(id)
    }
    page.value = 1
    clearSelection()
  } catch {
    folderStocks.value = []
  } finally {
    loading.value = false
  }
}

// 搜索防抖 300ms
const onSearchInput = useDebounceFn(() => {
  page.value = 1
}, 300)

// ---- 多选 ----
const selected = ref<Stock[]>([])
const hasSelected = computed(() => selected.value.length > 0)
function onSelectionChange(rows: Stock[]) {
  selected.value = rows
}
function clearSelection() {
  selected.value = []
}

// ---- 操作：移出 ----
async function onRemove(row: Stock) {
  if (!currentFolderId.value) {
    ElMessage.warning('「全部」视图下无法移出，请先选择具体文件夹')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将「${row.name}」移出自选吗？`,
      '移出确认',
      { type: 'warning' },
    )
    await removeStock(currentFolderId.value, row.code)
    ElMessage.success('已移出')
    await reload()
  } catch {
    // 取消或失败
  }
}

async function onBatchRemove() {
  if (!currentFolderId.value) {
    ElMessage.warning('「全部」视图下无法批量移出，请先选择具体文件夹')
    return
  }
  if (selected.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selected.value.length} 只股票移出自选吗？`,
      '批量移出确认',
      { type: 'warning' },
    )
    await Promise.all(
      selected.value.map((s) => removeStock(currentFolderId.value!, s.code)),
    )
    ElMessage.success(`已移出 ${selected.value.length} 只`)
    await reload()
  } catch {
    // 取消或失败
  }
}

// ---- 操作：移动 ----
async function onMove(row: Stock, targetId: string) {
  const toId = Number(targetId)
  if (!currentFolderId.value || toId === currentFolderId.value) return
  try {
    await moveStock(currentFolderId.value, toId, row.code)
    ElMessage.success('已移动')
    await reload()
  } catch {
    // 失败已由拦截器处理
  }
}

// ---- 新建文件夹 ----
const createDialogVisible = ref(false)
const newFolderName = ref('')
const creating = ref(false)

function openCreateFolder() {
  newFolderName.value = ''
  createDialogVisible.value = true
}

async function onCreateFolder() {
  const name = newFolderName.value.trim()
  if (!name) {
    ElMessage.warning('请输入文件夹名')
    return
  }
  creating.value = true
  try {
    await createFolder(name)
    ElMessage.success('文件夹已创建')
    createDialogVisible.value = false
    await loadFolders()
  } catch {
    // 失败已处理
  } finally {
    creating.value = false
  }
}

// ---- 删除文件夹 ----
async function onDeleteFolder(f: WatchFolder) {
  try {
    await ElMessageBox.confirm(
      `确定删除文件夹「${f.name}」吗？${f.codes.length > 0 ? `文件夹内含 ${f.codes.length} 只股票，将一并移出。` : ''}`,
      '删除文件夹',
      { type: 'warning' },
    )
    await deleteFolder(f.id)
    ElMessage.success('文件夹已删除')
    if (activeKey.value === String(f.id)) activeKey.value = 'all'
    await loadFolders()
    await loadStocks()
  } catch {
    // 取消
  }
}

// ---- 添加股票弹窗 ----
const addDialogVisible = ref(false)
const addFolderId = ref<number | null>(null)
const addStockCode = ref<string>('')
const adding = ref(false)
const stockOptions = ref<Stock[]>([])
const stockSearching = ref(false)

function searchStock(query: string) {
  stockSearching.value = true
  const q = query.trim().toLowerCase()
  if (!q) {
    stockOptions.value = allStocks.slice(0, 20)
  } else {
    stockOptions.value = allStocks
      .filter((s) => s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
      .slice(0, 30)
  }
  stockSearching.value = false
}

async function onAddStock() {
  if (!addFolderId.value) {
    ElMessage.warning('请选择目标文件夹')
    return
  }
  if (!addStockCode.value) {
    ElMessage.warning('请选择要添加的股票')
    return
  }
  adding.value = true
  try {
    await addStock(addFolderId.value, addStockCode.value)
    ElMessage.success('已添加到自选')
    addDialogVisible.value = false
    addStockCode.value = ''
    await reload()
  } catch {
    // 失败已处理
  } finally {
    adding.value = false
  }
}

// ---- 工具 ----
function formatPrice(v: number) {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function reload() {
  await loadFolders()
  await loadStocks()
}

onMounted(async () => {
  await loadFolders()
  await loadStocks()
})
</script>

<style scoped>
.watchlist-layout {
  display: flex;
  gap: var(--sp-lg);
  align-items: stretch;
  flex: 1;
  min-height: 0;
}
.folder-panel {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.folder-panel .tree {
  flex: 1;
  overflow-y: auto;
}
.folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.folder-del {
  color: var(--text-disabled);
  width: 14px;
  height: 14px;
  margin-left: 4px;
  border-radius: var(--r-sm);
}
.folder-del:hover {
  color: var(--rise);
  background: var(--rise-dim);
}
.main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-md);
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
.pager {
  display: flex;
  justify-content: flex-end;
  padding: var(--sp-md) var(--sp-lg);
  border-top: 1px solid var(--border-base);
}
.add-dialog-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.dialog-hint {
  font-size: 12px;
  color: var(--text-disabled);
  margin: 0;
}
</style>
