/**
 * 推广投放（推广精投）API
 * 公开部分：前台展示页效果对比 / 智能热搜 / 商品热榜（只读）
 * 管理部分：平台列表 / 投放矩阵 / 保存执行 / 历史版本
 */
import { get, post } from './request'

export interface AdPlatform {
  id: number
  code: string
  name: string
  logo_url: string
  sort_order: number
}

export interface MetricSnapshot {
  metric_key: string
  before_value: string
  after_value: string
  unit: string
  lower_is_better: boolean
  change_pct: number | null
  updated_at: string
}

export interface HotSearchItem {
  id: number
  keyword: string
  keyword_zh: string
  keyword_ar: string
  heat: number
  trend: 'up' | 'flat' | 'down'
  platform_code: string
  platform_name: string
}

export interface HotProductItem {
  id: number
  spu_id: number
  spu_name: string
  spu_name_en: string
  spu_name_ar: string
  spu_image: string
  heat: number
  reason: string
  reason_zh: string
  reason_ar: string
}

export interface CampaignCell {
  amount: string | null
  prev_amount: string | null
  version: number
  status: 'executing' | 'done' | 'failed' | null
}

export interface CampaignRow {
  spu_id: number
  spu_name: string
  spu_name_en: string
  spu_name_ar: string
  spu_image: string
  cells: Record<string, CampaignCell>
}

export interface CampaignMatrix {
  count: number
  results: CampaignRow[]
  platforms: AdPlatform[]
}

export interface CampaignHistoryItem {
  id: number
  spu_id: number
  platform_code: string
  amount: string
  version: number
  status: string
  executed_at: string | null
  note: string
  operator: string
  created_at: string
}

export interface CampaignSaveItem {
  spu_id: number
  platform_code: string
  amount: string
  base_version: number
}

export interface CampaignSaveResult {
  saved: { spu_id: number; platform_code: string; version: number; amount: string; status: string }[]
}

/** 前台多平台指标面板：单平台一行（含当前 4 指标 + 走势 + 涨跌）。 */
export interface PlatformMetric {
  platform_code: string
  platform_name: string
  logo_url: string
  metrics: {
    search: number
    click: number
    order: number
    conversion_rate: number
  }
  series: {
    search: number[]
    click: number[]
    order: number[]
    conversion: number[]
  }
  trend: {
    search: 'up' | 'flat' | 'down'
    click: 'up' | 'flat' | 'down'
    order: 'up' | 'flat' | 'down'
    conversion: 'up' | 'flat' | 'down'
  }
  delta_pct: {
    search: number
    click: number
    order: number
    conversion: number
  }
}

/** 单商品在指定平台上的本周指标（周一 ~ 今天）。 */
export interface ProductWeeklyItem {
  spu_id: number
  spu_name: string
  spu_name_en: string
  spu_name_ar: string
  spu_image: string
  metrics: {
    search: number
    click: number
    order: number
    conversion_rate: number
  }
  weekly: {
    search: number[]
    click: number[]
    order: number[]
  }
  order_share: number
}

export interface ProductWeeklyResponse {
  platform: string
  platform_name: string
  days: string[]
  items: ProductWeeklyItem[]
}

export const adsAPI = {
  // 前台展示页（公开）
  getInsightOverview: () => get<{ metrics: MetricSnapshot[] }>('/ads/insight/overview'),
  getHotSearches: () => get<{ results: HotSearchItem[] }>('/ads/insight/hot-searches'),
  getHotProducts: () => get<{ results: HotProductItem[] }>('/ads/insight/hot-products'),
  getPlatformMetrics: () => get<{ results: PlatformMetric[] }>('/ads/insight/platform-metrics'),
  getProductWeekly: (platform: string) =>
    get<ProductWeeklyResponse>('/ads/insight/product-weekly', { platform }),

  // 管理端投放操作
  getPlatforms: () => get<{ results: AdPlatform[] }>('/ads/admin/platforms'),
  getCampaigns: (params?: { page?: number; per_page?: number }) =>
    get<CampaignMatrix>('/ads/admin/campaigns', params as Record<string, unknown>),
  saveCampaigns: (items: CampaignSaveItem[]) =>
    post<CampaignSaveResult>('/ads/admin/campaigns/save', { items }),
  getCampaignHistory: (spuId: number, platformCode: string) =>
    get<{ results: CampaignHistoryItem[] }>('/ads/admin/campaigns/history', {
      spu_id: spuId,
      platform_code: platformCode,
    }),
}
