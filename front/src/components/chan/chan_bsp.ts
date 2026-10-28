// chan_bsp.ts — 买卖点覆盖层（circle + text 标签，买红 #F6465D 卖绿 #2EBD85）
// design.md D5：marker + 文本标签（1B/2B/L2B/3B 等），用 overlay 的 circle + text figure。
//
// 实现方式：每个买卖点注入 1 个点 (t, v) 到 overlay.points，
// klinecharts 自动转为 coordinate。extendData 存 {isBuy, types, pointIndex}。
import { registerOverlay, type OverlayFigure } from 'klinecharts'
import { bspLabels } from '@/utils/bsp'

/** 买卖点 overlay 元数据（存于 extendData） */
export interface ChanBspMeta {
  isBuy: boolean
  types: string[]
  /** 在 overlay.points / coordinates 中的索引 */
  pointIndex: number
}

/** 买点颜色 — design.css --rise */
const BUY_COLOR = '#F6465D'
/** 卖点颜色 — design.css --fall */
const SELL_COLOR = '#2EBD85'

let registered = false

/** 注册买卖点覆盖层。幂等，重复调用安全。 */
export function registerChanBsp(): void {
  if (registered) return
  registered = true

  registerOverlay({
    name: 'chan_bsp',
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: (params): OverlayFigure[] => {
      const { overlay, coordinates } = params
      const meta = overlay.extendData as ChanBspMeta[] | undefined
      if (!meta || meta.length === 0 || !coordinates || coordinates.length === 0) return []

      const figures: OverlayFigure[] = []
      meta.forEach((m) => {
        const c = coordinates[m.pointIndex]
        if (!c) return

        const color = m.isBuy ? BUY_COLOR : SELL_COLOR
        const labels = bspLabels(m.types, m.isBuy)
        const label = labels.length > 0 ? labels.join('/') : (m.isBuy ? 'B' : 'S')

        // circle marker
        figures.push({
          type: 'circle',
          attrs: { x: c.x, y: c.y, r: 4 },
          styles: {
            style: 'fill',
            color,
            borderColor: color,
            borderSize: 1,
            borderStyle: 'solid',
            borderDashedValue: [2, 2],
          },
        })

        // text label — 买点标在 marker 下方，卖点标在上方
        const textY = m.isBuy ? c.y + 18 : c.y - 8
        figures.push({
          type: 'text',
          attrs: { x: c.x, y: textY, text: label, align: 'center', baseline: 'top' },
          styles: {
            style: 'fill',
            color,
            size: 11,
            weight: '600',
            family: 'JetBrains Mono, monospace',
            borderStyle: 'solid',
            borderDashedValue: [2, 2],
            borderSize: 0,
            borderColor: 'transparent',
            borderRadius: 2,
            backgroundColor: 'transparent',
            paddingLeft: 2,
            paddingRight: 2,
            paddingTop: 1,
            paddingBottom: 1,
          },
        })
      })
      return figures
    },
  })
}
