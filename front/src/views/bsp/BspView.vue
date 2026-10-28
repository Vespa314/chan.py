<template>
  <div class="page-layout">
    <!-- 左侧菜单栏 -->
    <aside class="panel sidebar reveal reveal--1">
      <div class="sidebar__head">
        买卖点
        <span class="spacer"></span>
      </div>
      <div class="tree">
        <div class="sidebar__group">
          <div class="sidebar__group-label">方向</div>
          <div
            class="tree__item"
            :class="{ 'is-active': query.direction === '' }"
            @click="setDirection('')"
          >
            <el-icon class="tree__icon"><TrendCharts /></el-icon>
            <span>全部方向</span>
            <span class="count">{{ stats.total }}</span>
          </div>
          <div
            class="tree__item"
            :class="{ 'is-active': query.direction === 'buy' }"
            @click="setDirection('buy')"
          >
            <el-icon class="tree__icon"><Top /></el-icon>
            <span>买点</span>
            <span class="count">{{ stats.buy }}</span>
          </div>
          <div
            class="tree__item"
            :class="{ 'is-active': query.direction === 'sell' }"
            @click="setDirection('sell')"
          >
            <el-icon class="tree__icon"><Bottom /></el-icon>
            <span>卖点</span>
            <span class="count">{{ stats.sell }}</span>
          </div>
        </div>
        <div class="sidebar__group">
          <div class="sidebar__group-label">周期</div>
          <div
            v-for="kl in klOptions"
            :key="kl.value"
            class="tree__item"
            :class="{ 'is-active': query.kl_type === kl.value }"
            @click="setKlType(kl.value)"
          >
            <el-icon class="tree__icon"><Calendar /></el-icon>
            <span>{{ kl.label }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主面板 -->
    <div class="main-panel">
      <div class="bsp-page">
        <!-- 查询筛选区 -->
        <div class="toolbar reveal reveal--1">
          <el-select v-model="query.kl_type" placeholder="周期" style="width: 130px" @change="onQueryChange">
            <el-option v-for="kl in klOptions" :key="kl.value" :label="kl.label" :value="kl.value" />
          </el-select>
          <el-input
            v-model="query.keyword"
            placeholder="名称 / 编码"
            style="width: 180px"
            clearable
            @input="onSearchInput"
            :prefix-icon="Search"
          />
          <el-select v-model="query.bsp_type" placeholder="买卖点类型" style="width: 150px" @change="onQueryChange">
            <el-option label="全部类型" value="" />
            <el-option v-for="t in ALL_BSP_LABELS" :key="t" :label="t" :value="t" />
          </el-select>
          <el-select v-model="query.direction" placeholder="方向" style="width: 120px" @change="onQueryChange">
            <el-option label="全部方向" value="" />
            <el-option label="买" value="buy" />
            <el-option label="卖" value="sell" />
          </el-select>
          <button class="btn btn--primary" @click="onQuery">查询</button>
          <button class="btn btn--default" @click="onReset">重置</button>
        </div>

        <!-- 操作工具条 -->
        <div class="toolbar reveal reveal--2">
          <span class="text-secondary" style="font-size: 12px">
            已选 <span class="num">{{ selectedCount }}</span> 项
          </span>
          <span class="spacer"></span>
          <button class="btn btn--default" :disabled="!hasSelected" @click="onBatchWatchlist">
            批量加入自选
          </button>
          <button class="btn btn--default" :disabled="!hasSelected" @click="onBatchMonitor">
            加入监控
          </button>
        </div>

        <!-- 结果区 -->
        <div class="panel reveal reveal--3">
          <el-tabs v-model="activeTab" class="bsp-tabs">
            <el-tab-pane label="结果列表" name="list">
              <div class="tbl-wrap" v-loading="loading">
                <el-table
                  :data="records"
                  empty-text="暂无买卖点记录"
                  @selection-change="onSelectionChange"
                  row-key="id"
                >
                  <el-table-column type="selection" width="44" reserve-selection />
                  <el-table-column label="名称 / 编码" width="180">
                    <template #default="{ row }">
                      <div class="cell-stock">
                        <span class="nm">{{ row.name }}</span>
                        <span class="cd mono">{{ row.code }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="股价" width="100" align="right">
                    <template #default="{ row }">
                      <span class="num">{{ formatPrice(row.current_price) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="行业" min-width="160">
                    <template #default="{ row }">
                      <IndustryBadges :industries="row.industries" />
                    </template>
                  </el-table-column>
                  <el-table-column label="买卖点类型" width="110">
                    <template #default="{ row }">
                      <span class="badge" :class="row.direction === 'buy' ? 'badge--rise' : 'badge--fall'">
                        {{ row.bsp_type }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="方向" width="80">
                    <template #default="{ row }">
                      <span class="badge" :class="row.direction === 'buy' ? 'badge--rise' : 'badge--fall'">
                        {{ row.direction === 'buy' ? '买' : '卖' }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="买卖点价格" width="120" align="right">
                    <template #default="{ row }">
                      <span class="num">{{ formatPrice(row.bsp_price) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="买卖点日期" width="120">
                    <template #default="{ row }">
                      <span class="num">{{ formatDate(row.bsp_date) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="周期" width="90">
                    <template #default="{ row }">
                      <span class="num">{{ klLabel(row.kl_type) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="100" align="right">
                    <template #default="{ row }">
                      <button class="row-action" @click="openNesting(row)">区间套</button>
                    </template>
                  </el-table-column>
                  <template #empty>
                    <EmptyState description="暂无买卖点记录，请调整查询条件" />
                  </template>
                </el-table>
              </div>
              <div class="pager" v-if="total > 0">
                <el-pagination
                  v-model:current-page="query.page"
                  v-model:page-size="query.page_size"
                  :total="total"
                  :page-sizes="[20]"
                  layout="total, prev, pager, next, jumper"
                  background
                  @current-change="loadList"
                />
              </div>
            </el-tab-pane>

            <el-tab-pane label="板块聚合" name="sector">
              <div class="tbl-wrap" v-loading="aggLoading">
                <el-table :data="aggregate" empty-text="暂无聚合数据">
                  <el-table-column label="行业" min-width="160">
                    <template #default="{ row }">
                      <span class="badge badge--default">{{ row.industry }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="买点股票数" width="140" align="right">
                    <template #default="{ row }">
                      <span class="num text-rise">{{ row.buy_count }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="卖点股票数" width="140" align="right">
                    <template #default="{ row }">
                      <span class="num text-fall">{{ row.sell_count }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="合计" width="120" align="right">
                    <template #default="{ row }">
                      <span class="num">{{ row.total }}</span>
                    </template>
                  </el-table-column>
                  <template #empty>
                    <EmptyState description="暂无板块聚合数据" />
                  </template>
                </el-table>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>

    <!-- 区间套抽屉 -->
    <NestingDrawer
      v-model:visible="nestingVisible"
      :record="nestingRecord"
    />

    <!-- 批量加入自选弹窗 -->
    <el-dialog v-model="watchlistDialogVisible" title="批量加入自选" width="420px" append-to-body>
      <div class="add-dialog-body">
        <div class="form-row">
          <label>目标文件夹</label>
          <el-select v-model="watchlistFolderId" placeholder="选择文件夹" style="width: 100%">
            <el-option v-for="f in watchFolders" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </div>
        <p class="dialog-hint">
          选中的 {{ selectedCount }} 只股票将按 code 去重后加入目标文件夹。
        </p>
      </div>
      <template #footer>
        <el-button @click="watchlistDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addingWatch" @click="confirmBatchWatchlist">确认加入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts, Top, Bottom, Calendar, Search } from '@element-plus/icons-vue'
import { useDebounceFn } from '@vueuse/core'
import IndustryBadges from '@/components/ui/IndustryBadges.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import NestingDrawer from './NestingDrawer.vue'
import { getBspList, getBspAggregate, type BspQuery } from '@/api/modules/bsp'
import { getFolders, addStock, type WatchFolder } from '@/api/modules/watchlist'
import { ALL_BSP_LABELS } from '@/utils/bsp'
import type { BspRecord, BspAggregate } from '@/api/types'

const klOptions = [
  { label: '日线', value: 'D' },
  { label: '60分钟', value: '60m' },
  { label: '30分钟', value: '30m' },
  { label: '15分钟', value: '15m' },
  { label: '5分钟', value: '5m' },
  { label: '1分钟', value: '1m' },
  { label: '周线', value: 'W' },
]

function klLabel(v: string) {
  return klOptions.find((k) => k.value === v)?.label || v
}

// ---- 查询 ----
const query = reactive<BspQuery>({
  page: 1,
  page_size: 20,
  keyword: '',
  bsp_type: '',
  direction: '',
  kl_type: '',
})

const activeTab = ref<'list' | 'sector'>('list')
const loading = ref(false)
const records = ref<BspRecord[]>([])
const total = ref(0)

// 统计（侧栏 count）
const stats = reactive({ total: 0, buy: 0, sell: 0 })

async function loadList() {
  loading.value = true
  try {
    const res = await getBspList(query)
    records.value = res.list
    total.value = res.total
    // 粗略统计（基于当前查询条件下的总数）
    stats.total = res.total
    // 买/卖数需额外查询，这里用当前页近似
    stats.buy = res.list.filter((r) => r.direction === 'buy').length
    stats.sell = res.list.filter((r) => r.direction === 'sell').length
  } catch {
    records.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 板块聚合
const aggLoading = ref(false)
const aggregate = ref<BspAggregate[]>([])
async function loadAggregate() {
  aggLoading.value = true
  try {
    aggregate.value = await getBspAggregate()
  } catch {
    aggregate.value = []
  } finally {
    aggLoading.value = false
  }
}

// 搜索防抖 300ms
const onSearchInput = useDebounceFn(() => {
  query.page = 1
  loadList()
}, 300)

function onQueryChange() {
  query.page = 1
  loadList()
}

function onQuery() {
  query.page = 1
  loadList()
}

function onReset() {
  query.keyword = ''
  query.bsp_type = ''
  query.direction = ''
  query.kl_type = ''
  query.page = 1
  loadList()
}

function setDirection(d: 'buy' | 'sell' | '') {
  query.direction = d
  onQueryChange()
}
function setKlType(v: string) {
  query.kl_type = v
  onQueryChange()
}

// ---- 多选 ----
const selected = ref<BspRecord[]>([])
const selectedCount = ref(0)
const hasSelected = ref(false)
function onSelectionChange(rows: BspRecord[]) {
  selected.value = rows
  selectedCount.value = rows.length
  hasSelected.value = rows.length > 0
}

// ---- 区间套 ----
const nestingVisible = ref(false)
const nestingRecord = ref<BspRecord | null>(null)
function openNesting(row: BspRecord) {
  nestingRecord.value = row
  nestingVisible.value = true
}

// ---- 批量加入自选 ----
const watchlistDialogVisible = ref(false)
const watchlistFolderId = ref<number | null>(null)
const watchFolders = ref<WatchFolder[]>([])
const addingWatch = ref(false)

async function onBatchWatchlist() {
  if (!hasSelected.value) return
  try {
    watchFolders.value = await getFolders()
    watchlistFolderId.value = watchFolders.value[0]?.id ?? null
    watchlistDialogVisible.value = true
  } catch {
    // 失败已处理
  }
}

async function confirmBatchWatchlist() {
  if (!watchlistFolderId.value) {
    ElMessage.warning('请选择目标文件夹')
    return
  }
  addingWatch.value = true
  try {
    // 按 code 去重
    const codes = Array.from(new Set(selected.value.map((r) => r.code)))
    await Promise.all(codes.map((c) => addStock(watchlistFolderId.value!, c)))
    ElMessage.success(`已加入 ${codes.length} 只到自选`)
    watchlistDialogVisible.value = false
  } catch {
    // 失败已处理
  } finally {
    addingWatch.value = false
  }
}

// ---- 加入监控 ----
function onBatchMonitor() {
  if (!hasSelected.value) return
  ElMessage.success(`已将 ${selectedCount.value} 条记录加入监控（演示）`)
}

// ---- 工具 ----
function formatPrice(v: number) {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function formatDate(ts: number) {
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

onMounted(() => {
  loadList()
  loadAggregate()
})
</script>

<style scoped>
.bsp-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
  flex: 1;
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
.bsp-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 var(--sp-md);
}
.bsp-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--border-base);
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
