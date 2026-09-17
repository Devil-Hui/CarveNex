import { resolveMediaUrl, apiOrigin } from '../api/chat'

/**
 * 统一商品图片 URL 解析，返回可安全渲染的 src。
 * - 空值 → undefined（不渲染）
 * - 回环地址 / 相对路径 → 解析为后端绝对 URL（修复「商品图片无法显示」）
 */
export function optionalMediaUrl(value: string | null | undefined): string | undefined {
  return resolveMediaUrl(value) || undefined
}

/**
 * 返回后端同源基础地址（用于把 CDN 地址改写成本地后端源做兜底）。
 * 本地源托管在后端 Django（/media/），因此复用 apiOrigin 而非 window.location。
 */
export function localFallbackOrigin(): string {
  return apiOrigin()
}