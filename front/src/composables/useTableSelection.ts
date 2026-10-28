import { ref, computed } from 'vue'

/** 表格多选 composable */
export function useTableSelection<T extends { id: number }>() {
  const selected = ref<T[]>([])

  const selectedIds = computed(() => selected.value.map((i) => i.id))
  const selectedCount = computed(() => selected.value.length)
  const hasSelected = computed(() => selected.value.length > 0)

  function onSelectionChange(rows: T[]) {
    selected.value = rows
  }
  function clear() {
    selected.value = []
  }

  return {
    selected,
    selectedIds,
    selectedCount,
    hasSelected,
    onSelectionChange,
    clear,
  }
}
