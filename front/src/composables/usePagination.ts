import { ref, computed } from 'vue'

/** 通用分页 composable — 服务端分页 20/页 */
export function usePagination(defaultSize = 20) {
  const page = ref(1)
  const pageSize = ref(defaultSize)
  const total = ref(0)

  const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

  function setPage(p: number) {
    page.value = p
  }
  function setTotal(t: number) {
    total.value = t
  }
  function reset() {
    page.value = 1
  }

  return {
    page,
    pageSize,
    total,
    totalPages,
    setPage,
    setTotal,
    reset,
  }
}
