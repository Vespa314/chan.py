import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * v-permission 指令 — 仅控制管理类按钮显隐（design.md D16）
 * 业务按钮全部开放，不使用此指令。
 *
 * 用法：v-permission="'manage'" 或 v-permission="['manage','user:create']"
 * 无权限时移除该元素。
 */
export const permission: Directive = {
  mounted(el, binding) {
    const auth = useAuthStore()
    const value = binding.value
    const codes = Array.isArray(value) ? value : [value]
    const ok = codes.some((c: string) => auth.hasPerm(c))
    if (!ok) {
      el.parentNode?.removeChild(el)
    }
  },
}
