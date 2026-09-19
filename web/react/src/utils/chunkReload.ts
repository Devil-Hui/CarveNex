// 「部署后旧 chunk 404」自愈：自动刷新一次，避免用户看到
// React Router 的 "Unexpected Application Error!" 页面。
//
// 背景：Cloudflare Pages 每次发布都会把 assets/*.js 换成新的 hash 文件名。
// 用户浏览器里还开着发布前的页面（或命中缓存里的旧 index.html）时，再进入某个
// 懒加载路由（如 admin.carvenex.com → /admin/login → AdminLogin-xxxx.js），
// 旧 chunk 已被删除 → 浏览器抛
//   TypeError: Failed to fetch dynamically imported module: <url>
// React Router 内部错误边界把它渲染成 "Unexpected Application Error!"。
//
// 处理方式：捕获这类加载失败后自动刷新，用新的 index.html 拿到与之匹配的新 chunk。
// 用 sessionStorage 做 10s 冷却：若刷新后仍失败（说明是真故障而非版本错位），
// 不再继续刷新，交给错误边界展示。

import { lazy, type ComponentType } from 'react'

const RELOAD_AT_KEY = 'carvenex:chunkReloadAt'
const RELOAD_COOLDOWN_MS = 10_000

/**
 * 触发一次自动刷新。处于冷却期内（即刷新过后仍然失败）返回 false，由调用方决定后续。
 */
export function reloadForNewChunks(): boolean {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_AT_KEY) ?? 0)
    if (Number.isFinite(last) && Date.now() - last < RELOAD_COOLDOWN_MS) {
      return false
    }
    sessionStorage.setItem(RELOAD_AT_KEY, String(Date.now()))
  } catch {
    // 隐私模式 / sessionStorage 被禁用：无法防抖，直接刷新一次
  }
  window.location.reload()
  return true
}

/**
 * 监听 Vite 的 vite:preloadError 事件（动态 import 的 chunk 及其静态依赖预加载失败时派发）。
 * 覆盖未被 React.lazy 包装的 import() 以及 CSS preload 失败。
 */
export function installChunkReloadHandler(): void {
  window.addEventListener('vite:preloadError', (event) => {
    if (reloadForNewChunks()) {
      // 已安排刷新，阻止 Vite 继续抛出该错误
      event.preventDefault()
    }
  })
}

/**
 * React.lazy 包装：动态 import 失败时自动刷新。
 * 刷新期间返回一个永不 resolve 的 Promise，让 Suspense 保持 loading 占位，
 * 避免错误界面在页面卸载前闪一下。
 *
 * 泛型约束与 React.lazy 一致但避免 `any`：`Record<string, never>` 的值类型是 never，
 * 可赋给任意组件 props（含必填项），因此既能接受 FC、FC<Props>，也能通过 React.lazy
 * 自身的 `ComponentType<any>` 约束。
 */
export function lazyWithReload<T extends ComponentType<Record<string, never>>>(
  factory: () => Promise<{ default: T }>,
) {
  return lazy(() =>
    factory().catch((error: unknown) => {
      if (reloadForNewChunks()) {
        return new Promise<never>(() => {})
      }
      throw error
    }),
  )
}
