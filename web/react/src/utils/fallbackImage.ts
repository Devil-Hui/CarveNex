/**
 * 图片加载兜底（failover）：
 * - 优先用 CDN / 远程绝对地址，加载失败自动切到本地后端源（同源 Django 托管 /media/）
 * - 记忆 CDN 域名可用性：一旦某域名近期加载失败，当前会话后续图片直接用本地源，避免反复超时（省时间/带宽）
 * - 定时（探活）恢复：CDN 恢复可用后自动切回原地址，节省本地带宽/内存压力
 * - 全程用户无感：切换一次即定格，不闪烁、不发多余请求
 */

import { apiOrigin, resolveMediaUrl } from '../api/chat'

/** 一个 CDN 域名在一段时间内的可用性状态（模块级，跨组件共享） */
type DomainState = {
  /** 本次判定为不可用的起始时间戳 */
  downAt: number
  /** 最后成功时间戳（用于防止恢复抖动） */
  okAt: number
  /** 黑名单过期后，是否已进入首轮探活 */
  unchecked: boolean
}

const domainStates = new Map<string, DomainState>()

/** CDN 域名连续失败 → 直接用本地源的最小黑名单时长（毫秒） */
const DOWN_COOLDOWN = 30_000
/** 黑名单最长兜底（毫秒）：超过该值后强制放行一次 CDN 尝试（探活） */
const DOWN_COOLDOWN_MAX = 120_000
/** CDN 回落后，本地源最短展示时长（毫秒），避免在一个页面里反复横跳 */
const LOCAL_MIN_LIFETIME = 15_000

function hostOf(url: string): string | null {
  try {
    return new URL(url).host
  } catch {
    return null
  }
}

/**
 * 判断 CDN 域名当前是否被判定为不可用（黑名单中）。
 */
export function isCdnDomainDown(url: string): boolean {
  const host = hostOf(url)
  if (!host) return false
  const st = domainStates.get(host)
  if (!st || !st.downAt) return false
  const elapsed = Date.now() - st.downAt
  if (elapsed < DOWN_COOLDOWN) return true
  // 黑名单已过期：此轮先放行一次「探活」，若探活失败会重新记录 downAt
  if (!st.unchecked) {
    st.unchecked = true
  }
  return false
}

/**
 * 记录一次 CDN 加载失败。跳过的场景：本地源刚切回 CDN 未满 LOCAL_MIN_LIFETIME。
 */
export function markCdnDown(url: string): void {
  const host = hostOf(url)
  if (!host) return
  const prev = domainStates.get(host)
  if (prev?.okAt && Date.now() - prev.okAt < LOCAL_MIN_LIFETIME) return
  domainStates.set(host, { downAt: Date.now(), okAt: prev?.okAt || 0, unchecked: false })
}

/**
 * 记录一次 CDN 加载成功（onLoad 或探活成功）。
 */
export function markCdnOk(url: string): void {
  const host = hostOf(url)
  if (!host) return
  domainStates.set(host, { downAt: 0, okAt: Date.now(), unchecked: false })
}

/**
 * 把 CDN/远程绝对地址改写为「本地后端源」地址（兜底源）。
 * 保留原路径 /原 query，仅替换域名；本机/相对地址原样返回。
 */
export function toLocalFallback(url: string): string {
  const loc = apiOrigin()
  if (url.startsWith(loc) || url.startsWith('/')) return url
  try {
    const u = new URL(url)
    if (u.host === new URL(loc).host) return url
    // 提取对象 key（去掉顶层 /media/ 前缀）：R2 键形如 products/2026/MM/DD/uuid.jpg
    let key = decodeURIComponent(u.pathname)
    if (key.startsWith('/media/')) key = key.slice('/media/'.length)
    else key = key.replace(/^\//, '')
    // 兜底源 = 后端 R2 代理端点（服务端持有 R2 密钥，从真实对象存储读字节），
    // 保证 CDN 公网不可达时也能从 R2 取到图，无需依赖本地磁盘副本。
    // key 含子路径用 path 段传递（/api/media/r2/）内保留 /。
    return `${loc}/api/media/r2/${key}`
  } catch {
    return url
  }
}

export type FallbackSpec = {
  src: string
  /** 由 img 的 onError 触发：记录失败并切换（通过 options.forceLocal 由组件端重取） */
  onError: () => void
  onLoad: () => void
}

/**
 * 图片 failover 核心，给 <img> 用：
 * @param url  原始地址（可能为空）
 * @param opts.forceLocal 强制走本地兜底源（用于 onError 后重试）
 * @returns { src, onError, onLoad } 或 null（无可渲染地址时）
 *  - CDN 域名黑名单内 / forceLocal → 直接给本地源
 *  - 否则给原地址；失败切本地并记黑名单；成功记 ok
 */
export function createFallbackImage(
  url: string | null | undefined,
  opts?: { forceLocal?: boolean },
): FallbackSpec | null {
  const resolved = resolveMediaUrl(url)
  if (!resolved) return null
  if (resolved.startsWith('/')) return { src: resolved, onError: noop, onLoad: noop }

  if (opts?.forceLocal || isCdnDomainDown(resolved)) {
    return { src: toLocalFallback(resolved), onError: noop, onLoad: noop }
  }

  let failed = false
  return {
    src: resolved,
    onError: () => {
      if (failed) return
      failed = true
      markCdnDown(resolved)
    },
    onLoad: () => markCdnOk(resolved),
  }
}

function noop() {
  /* noop */
}

/** 供 <img onError> 直挂：域名黑名单判定下直接返回本地源（仍保留实时 onError 复位）。 */
export function fallbackSrc(url: string | null | undefined): string {
  const f = createFallbackImage(url)
  return f ? f.src : ''
}