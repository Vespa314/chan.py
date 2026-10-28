// chan_seg.ts — 线段覆盖层（蓝色折线 #3B82F6，line figure）
// design.md D5：自定义 overlay，createPointFigures 返回 line figure（两点折线）
//
// 实现方式同 chan_bi：overlay.points 按 [begin1, end1, begin2, end2, ...] 顺序注入。
import { registerOverlay, type OverlayFigure } from 'klinecharts'

/** 线段颜色 — design.css --accent-base */
const SEG_COLOR = '#3B82F6'

let registered = false

/** 注册线段覆盖层。幂等，重复调用安全。 */
export function registerChanSeg(): void {
  if (registered) return
  registered = true

  registerOverlay({
    name: 'chan_seg',
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: (params): OverlayFigure[] => {
      const { coordinates } = params
      if (!coordinates || coordinates.length < 2) return []

      const figures: OverlayFigure[] = []
      for (let i = 0; i + 1 < coordinates.length; i += 2) {
        const a = coordinates[i]
        const b = coordinates[i + 1]
        if (a == null || b == null) continue
        figures.push({
          type: 'line',
          attrs: { coordinates: [{ x: a.x, y: a.y }, { x: b.x, y: b.y }] },
          styles: {
            color: SEG_COLOR,
            size: 2.2,
            style: 'solid',
            smooth: false,
            dashedValue: [2, 2],
          },
        })
      }
      return figures
    },
  })
}
