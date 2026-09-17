// 前台页面统一布局模版
// 使用方式：<PageLayout><YourContent /></PageLayout>
// 自动包裹 Navigation + 内容区，后续可扩展 Footer
//
// 落地页（/）与推广精投页（/promo-precision）特殊处理：
// - 窗口宽度在 (900, 1440) 区间时，整页按 1440 设计宽度 CSS zoom 等比缩放，
//   保证窄窗口下看到的仍是同一个页面（与宽屏布局一致）。
// - 任何窗口宽度下都强制显示完整分类导航（forceFullNav=true）——前台页面
//   是品牌的统一门面，分类导航始终可见，不依赖断点切换。
// 下限 900 与 Footer(≤900 重排) 及落地页 editorial(md=900) 断点互补：
// 缩放区间内这些断点永不触发，行为在任意宽度下唯一确定。
// ≤900 为平板/手机，保留原生响应式；≥1440 为设计基准，无需缩放。

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import Navigation from '../Navigation/Navigation'
import Footer from '../Footer/Footer'

type PageLayoutProps = {
  children: ReactNode
}

const DESIGN_WIDTH = 1440
const SCALE_MIN_VW = 901

// Pages that should render at design width (1440) and scale-down on narrow viewports,
// and should always show the full category nav regardless of window size.
const FULL_NAV_PATHS = new Set(['/', '/promo-precision'])

function useLandingScale(enabled: boolean) {
  const stageRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const el = stageRef.current
    if (!enabled || !el) return

    const update = () => {
      const vw = window.innerWidth
      const active = vw >= SCALE_MIN_VW && vw < DESIGN_WIDTH
      el.style.zoom = active ? String(vw / DESIGN_WIDTH) : ''
    }

    update()
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('resize', update)
      el.style.zoom = ''
    }
  }, [enabled])

  return { stageRef }
}

export default function PageLayout({ children }: PageLayoutProps) {
  const { pathname } = useLocation()
  const isScaledPage = FULL_NAV_PATHS.has(pathname)
  const { stageRef } = useLandingScale(isScaledPage)

  // 前台页面始终显示完整分类导航——与断点、缩放区间解耦。
  return (
    <div ref={stageRef}>
      <Navigation forceFullNav={isScaledPage} />
      {children}
      <Footer />
    </div>
  )
}