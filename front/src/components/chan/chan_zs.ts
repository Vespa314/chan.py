// chan_zs.ts — 中枢覆盖层（灰框，rect figure；可配置颜色区分笔中枢/线段中枢）
// design.md D5：矩形。用 rect figure。
//
// 中枢由 (begin_t, end_t, low, high) 定义，是一个时间×价格的矩形框。
// 实现方式：每个中枢注入 4 个角点到 overlay.points（顺序：左上→右上→右下→左下），
// klinecharts 自动转为 coordinates。extendData 存每个中枢的 {level, startIndex}。
import { registerOverlay, type OverlayFigure } from 'klinecharts'

/** 中枢 overlay 元数据（存于 extendData，描述每个中枢在 points 中的位置） */
export interface ChanZsMeta {
  /** 'bi' 笔中枢（灰框） | 'seg' 线段中枢（蓝框） */
  level: 'bi' | 'seg'
  /** 在 overlay.points / coordinates 中的起始索引（每个中枢占 4 个点） */
  startIndex: number
}

/** 笔中枢颜色 — design.css zs-bi */
const ZS_BI_FILL = 'rgba(155, 161, 168, 0.10)'
const ZS_BI_BORDER = 'rgba(155, 161, 168, 0.55)'
/** 线段中枢颜色 — design.css zs-seg */
const ZS_SEG_FILL = 'rgba(59, 130, 246, 0.09)'
const ZS_SEG_BORDER = 'rgba(59, 130, 246, 0.65)'

let registered = false

/** 注册中枢覆盖层。幂等，重复调用安全。 */
export function registerChanZs(): void {
  if (registered) return
  registered = true

  registerOverlay({
    name: 'chan_zs',
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: (params): OverlayFigure[] => {
      const { overlay, coordinates } = params
      const meta = overlay.extendData as ChanZsMeta[] | undefined
      if (!meta || meta.length === 0 || !coordinates || coordinates.length === 0) return []

      const figures: OverlayFigure[] = []
      meta.forEach((m) => {
        const i = m.startIndex
        // 4 个角点：左上(begin,high) 右上(end,high) 右下(end,low) 左下(begin,low)
        const tl = coordinates[i]
        const tr = coordinates[i + 1]
        const br = coordinates[i + 2]
        const bl = coordinates[i + 3]
        if (!tl || !tr || !br || !bl) return

        const x = Math.min(tl.x, tr.x)
        const width = Math.abs(tr.x - tl.x)
        const y = Math.min(tl.y, bl.y)
        const height = Math.abs(bl.y - tl.y)
        if (width <= 0 || height <= 0) return

        const isSeg = m.level === 'seg'
        figures.push({
          type: 'rect',
          attrs: { x, y, width, height },
          styles: {
            style: 'stroke_fill',
            color: isSeg ? ZS_SEG_FILL : ZS_BI_FILL,
            borderColor: isSeg ? ZS_SEG_BORDER : ZS_BI_BORDER,
            borderSize: 1,
            borderStyle: isSeg ? 'solid' : 'dashed',
            borderDashedValue: [4, 3],
            borderRadius: 3,
          },
        })
      })
      return figures
    },
  })
}
