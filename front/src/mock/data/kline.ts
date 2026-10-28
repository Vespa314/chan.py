import type { ChanResult, KLine, Bi, Seg, ZS, BspPoint } from '@/api/types'

// ============================================================================
// chan.py K 线 mock 生成器 — 严格遵循 design.md D2 序列化契约
// 生成 120 根日线，从 K 线极值提取笔/线段/中枢/买卖点
// ============================================================================

const DAY = 86400000
const START = new Date('2026-07-01T00:00:00').getTime()

/** 确定性伪随机（种子固定，保证每次渲染一致） */
function mulberry32(seed: number) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** 生成 120 根日线 OHLCV */
function genKlines(seed: number, basePrice: number): KLine[] {
  const rand = mulberry32(seed)
  const klines: KLine[] = []
  let price = basePrice
  let trend = rand() > 0.5 ? 1 : -1
  let trendLen = 5 + Math.floor(rand() * 5)
  let i = 0

  while (i < 120) {
    // 每 trendLen 根切换趋势
    if (i % trendLen === 0) {
      trend *= -1
      trendLen = 5 + Math.floor(rand() * 5)
    }
    const volatility = basePrice * 0.02
    const open = price
    const drift = trend * volatility * (0.3 + rand() * 0.7)
    const noise = (rand() - 0.5) * volatility
    const close = +(open + drift + noise).toFixed(2)
    const high = +(Math.max(open, close) + rand() * volatility * 0.5).toFixed(2)
    const low = +(Math.min(open, close) - rand() * volatility * 0.5).toFixed(2)
    const volume = Math.floor(500000 + rand() * 3000000)
    klines.push({ timestamp: START + i * DAY, open, high, low, close, volume })
    price = close
    i++
  }
  return klines
}

/** 从 K 线极值提取笔端点 — 每 5-8 根一个，交替 UP/DOWN */
function genBi(klines: KLine[]): Bi[] {
  const bi: Bi[] = []
  const step = 6
  let dir: 'UP' | 'DOWN' = klines[step].high > klines[0].low ? 'UP' : 'DOWN'

  for (let i = 0; i + step < klines.length; i += step) {
    const seg = klines.slice(i, i + step + 1)
    if (dir === 'UP') {
      const peak = seg.reduce((a, b) => (b.high > a.high ? b : a))
      bi.push({
        begin: { t: seg[0].timestamp, v: seg[0].low },
        end: { t: peak.timestamp, v: peak.high },
        dir: 'UP',
        is_sure: true,
      })
      dir = 'DOWN'
    } else {
      const trough = seg.reduce((a, b) => (b.low < a.low ? b : a))
      bi.push({
        begin: { t: seg[0].timestamp, v: seg[0].high },
        end: { t: trough.timestamp, v: trough.low },
        dir: 'DOWN',
        is_sure: true,
      })
      dir = 'UP'
    }
  }
  return bi
}

/** 从笔合成线段 — 每 3-5 笔一段 */
function genSeg(bi: Bi[]): Seg[] {
  const seg: Seg[] = []
  const step = 4
  for (let i = 0; i + step <= bi.length; i += step) {
    const chunk = bi.slice(i, i + step)
    const dir = chunk[0].dir
    const begin = dir === 'UP' ? chunk[0].begin : chunk[0].begin
    const end = dir === 'UP' ? chunk[chunk.length - 1].end : chunk[chunk.length - 1].end
    seg.push({
      begin,
      end,
      dir,
      is_sure: true,
      level: 1,
    })
  }
  return seg
}

/** 从连续 3 笔重叠生成中枢 */
function genZs(bi: Bi[], level: 'bi' | 'seg' = 'bi'): ZS[] {
  const zs: ZS[] = []
  for (let i = 0; i + 2 < bi.length; i += 3) {
    const a = bi[i], b = bi[i + 1], c = bi[i + 2]
    const lows = [a.begin.v, a.end.v, b.begin.v, b.end.v, c.begin.v, c.end.v].filter(Boolean)
    const highs = lows // 简化
    const low = Math.max(...lows)
    const high = Math.min(...highs)
    if (low < high) {
      zs.push({
        begin_t: a.begin.t,
        end_t: c.end.t,
        low,
        high,
        mid: +((low + high) / 2).toFixed(2),
        level,
      })
    }
  }
  return zs
}

/** 在笔端点生成买卖点 — types 用原始枚举 */
function genBsp(bi: Bi[]): BspPoint[] {
  const bsp: BspPoint[] = []
  const types = ['1', '2', '2s', '3a', '3b', '1p']
  for (let i = 2; i < bi.length; i++) {
    if (Math.random() < 0.4) continue
    const b = bi[i]
    const isBuy = b.dir === 'UP'
    bsp.push({
      t: b.begin.t,
      v: b.begin.v,
      is_buy: isBuy,
      types: [types[i % types.length]],
    })
  }
  return bsp
}

/** 按 code 生成完整的 ChanResult */
export function genChanResult(code: string): ChanResult {
  // 从 code 派生种子
  let seed = 0
  for (let i = 0; i < code.length; i++) seed = (seed * 31 + code.charCodeAt(i)) | 0
  seed = Math.abs(seed) || 42

  // 基础价格按 code 区分
  const basePrice = code.startsWith('sh.600519') ? 1685
    : code.startsWith('sz.000001') ? 12
    : 10 + (seed % 200)

  const klines = genKlines(seed, basePrice)
  const bi = genBi(klines)
  const seg = genSeg(bi)
  const zs = genZs(bi, 'bi')
  const seg_zs = genZs(seg, 'seg')
  const bsp = genBsp(bi)

  return { klines, bi, seg, zs, seg_zs, bsp }
}

/** 缓存 */
const cache = new Map<string, ChanResult>()
export function getChanResult(code: string): ChanResult {
  if (!cache.has(code)) cache.set(code, genChanResult(code))
  return cache.get(code)!
}
