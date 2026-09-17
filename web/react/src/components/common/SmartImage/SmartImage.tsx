/**
 * SmartImage — 带 CDN 兜底（failover）的图片组件。
 *
 * 行为：
 * - 优先加载原地址（CDN / 远程绝对地址）
 * - 加载失败：自动切到本地后端源（同源 Django 托管 /media/），并记忆该域名状态，
 *   本会话后续同域名图片直接走本地，避免反复超时（用户无感、省带宽）
 * - 恢复：域名黑名单过期后定时放行一次“探活”，CDN 恢复则切回原地址（省本地流量）
 *
 * 用法与 <img> 基本一致：<SmartImage src={optionalMediaUrl(x)} alt="..." />
 */
import { useState, useEffect } from 'react'
import { createFallbackImage } from '../../../utils/fallbackImage'

export type SmartImageProps = Omit<
  React.ImgHTMLAttributes<HTMLImageElement>,
  'src'
> & {
  src: string | null | undefined
}

export default function SmartImage({ src, onError: userOnError, ...rest }: SmartImageProps) {
  // forceLocal 仅在“曾对同 src 失败过”时为 true，保证首次沿用 CDN、之后每次直接本地
  const [forceLocal, setForceLocal] = useState(false)
  const [fb, setFb] = useState(() => createFallbackImage(src))

  // src 变化（路由复用/KEY 切换）时重置 failover 状态
  useEffect(() => {
    setForceLocal(false)
  }, [src])

  useEffect(() => {
    setFb(createFallbackImage(src, { forceLocal }))
  }, [src, forceLocal])

  if (!fb) return null

  return (
    <img
      {...rest}
      src={fb.src}
      onLoad={(e) => {
        // 仅在“正在加载 CDN 源”时记录 ok；本地兜底源成功不代表 CDN 已恢复
        if (!forceLocal) fb.onLoad()
        rest.onLoad?.(e)
      }}
      onError={(e) => {
        fb.onError()
        setForceLocal(true)
        userOnError?.(e)
      }}
    />
  )
}