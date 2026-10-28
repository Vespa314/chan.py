import type { Stock } from '@/api/types'

/** A 股真实代码 + 行业 — mock 基础数据 */
export const stocks: Stock[] = [
  { code: 'sz.000001', name: '平安银行', industries: ['银行'], price: 11.85, change_pct: 1.23 },
  { code: 'sh.600519', name: '贵州茅台', industries: ['白酒', '食品饮料'], price: 1685.50, change_pct: -0.45 },
  { code: 'sz.000858', name: '五粮液', industries: ['白酒', '食品饮料'], price: 142.30, change_pct: 0.89 },
  { code: 'sh.600036', name: '招商银行', industries: ['银行'], price: 35.67, change_pct: 0.56 },
  { code: 'sz.000333', name: '美的集团', industries: ['家电'], price: 65.42, change_pct: -1.20 },
  { code: 'sh.600276', name: '恒瑞医药', industries: ['医药'], price: 48.15, change_pct: 2.34 },
  { code: 'sz.000725', name: '京东方A', industries: ['电子', '半导体'], price: 4.32, change_pct: 0.88 },
  { code: 'sh.601318', name: '中国平安', industries: ['保险', '金融'], price: 48.90, change_pct: -0.67 },
  { code: 'sz.002594', name: '比亚迪', industries: ['汽车', '新能源'], price: 245.60, change_pct: 3.45 },
  { code: 'sh.600887', name: '伊利股份', industries: ['食品饮料'], price: 28.75, change_pct: 0.12 },
  { code: 'sz.000568', name: '泸州老窖', industries: ['白酒'], price: 178.20, change_pct: 1.56 },
  { code: 'sh.601166', name: '兴业银行', industries: ['银行'], price: 18.43, change_pct: -0.34 },
  { code: 'sz.002415', name: '海康威视', industries: ['电子', '安防'], price: 32.18, change_pct: 0.78 },
  { code: 'sh.600030', name: '中信证券', industries: ['证券'], price: 25.34, change_pct: 1.89 },
  { code: 'sz.000651', name: '格力电器', industries: ['家电'], price: 38.92, change_pct: -0.56 },
  { code: 'sh.600009', name: '上海机场', industries: ['交通运输'], price: 52.10, change_pct: 0.45 },
  { code: 'sz.002230', name: '科大讯飞', industries: ['计算机', '人工智能'], price: 45.67, change_pct: 2.78 },
  { code: 'sh.600585', name: '海螺水泥', industries: ['建材'], price: 28.45, change_pct: -1.10 },
  { code: 'sz.300750', name: '宁德时代', industries: ['新能源', '电池'], price: 185.30, change_pct: 1.67 },
  { code: 'sh.601012', name: '隆基绿能', industries: ['新能源', '光伏'], price: 22.34, change_pct: -2.30 },
  { code: 'sz.000625', name: '长安汽车', industries: ['汽车'], price: 13.56, change_pct: 0.92 },
  { code: 'sh.600690', name: '海尔智家', industries: ['家电'], price: 25.78, change_pct: 0.34 },
  { code: 'sz.002241', name: '歌尔股份', industries: ['电子', '消费电子'], price: 23.45, change_pct: 1.23 },
  { code: 'sh.600809', name: '山西汾酒', industries: ['白酒'], price: 218.50, change_pct: 0.89 },
  { code: 'sz.000538', name: '云南白药', industries: ['医药'], price: 52.30, change_pct: -0.45 },
  { code: 'sh.601888', name: '中国中免', industries: ['商业百货'], price: 85.60, change_pct: 1.34 },
  { code: 'sz.002714', name: '牧原股份', industries: ['农业', '养殖'], price: 45.20, change_pct: -1.56 },
  { code: 'sh.600436', name: '片仔癀', industries: ['医药'], price: 235.40, change_pct: 0.67 },
  { code: 'sz.300059', name: '东方财富', industries: ['证券', '互联网金融'], price: 14.56, change_pct: 2.10 },
  { code: 'sh.600900', name: '长江电力', industries: ['电力'], price: 25.40, change_pct: 0.23 },
]

/** 按代码查找 */
export function findStock(code: string): Stock | undefined {
  return stocks.find((s) => s.code === code)
}

/** 所有行业列表 */
export const allIndustries: string[] = Array.from(
  new Set(stocks.flatMap((s) => s.industries)),
).sort()
