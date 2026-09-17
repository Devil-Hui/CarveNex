// 裁掉 logo.png 的白边，另存为 logo-trimmed.png（原图不动）
// bbox 由 scripts/logo-bbox-audit.cjs 多阈值扫描得出：
//   tol=48 时 1736x1610（含右下角极淡图库水印，会多留一大片白）
//   tol=64 时 1498x1160（水印被排除，只框真实图案）→ 采用，外加 PAD 像素防抗锯齿削边
const fs = require('fs')
const path = require('path')
const { chromium } = require('@playwright/test')

const SRC = 'public/static/images/logo.png'
const OUT = 'public/static/images/logo-trimmed.png'
const PAD = 6 // 0.4% 安全边，肉眼不可见
const RAW = { left: 278, top: 399, width: 1498, height: 1159 }
const BOX = {
  left: Math.max(0, RAW.left - PAD),
  top: Math.max(0, RAW.top - PAD),
  width: RAW.width + PAD * 2,
  height: RAW.height + PAD * 2,
}
const TARGET_W = 256 // 显示 45px 宽时约 5.7x，足够覆盖高 DPI

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto('http://localhost:12700/', { waitUntil: 'domcontentloaded' })

  const dataUrl = await page.evaluate(
    async ({ box, targetW }) => {
      const img = new Image()
      img.src = '/static/images/logo.png'
      await img.decode()

      const h = Math.round((box.height / box.width) * targetW)
      const c = document.createElement('canvas')
      c.width = targetW
      c.height = h
      const ctx = c.getContext('2d')
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      // 只取图案区域，缩放到 targetW 宽
      ctx.drawImage(img, box.left, box.top, box.width, box.height, 0, 0, targetW, h)
      return { url: c.toDataURL('image/png'), w: targetW, h }
    },
    { box: BOX, targetW: TARGET_W }
  )

  await browser.close()

  const buf = Buffer.from(dataUrl.url.replace(/^data:image\/png;base64,/, ''), 'base64')
  fs.writeFileSync(OUT, buf)

  const srcSize = fs.statSync(SRC).size
  const outSize = fs.statSync(OUT).size
  console.log(
    JSON.stringify(
      {
        source: SRC + '  ' + (srcSize / 1024).toFixed(0) + ' KB  (2048x2048)',
        output: OUT + '  ' + (outSize / 1024).toFixed(0) + ' KB  (' + dataUrl.w + 'x' + dataUrl.h + ')',
        aspect: (dataUrl.w / dataUrl.h).toFixed(4),
        sizeReduction: (100 - (outSize / srcSize) * 100).toFixed(1) + '% 更小',
        visibleAt45px: '45px 方框内图案渲染为 ' + 45 + 'x' + Math.round((dataUrl.h / dataUrl.w) * 45) + ' px（原图未裁时仅 38x35，且右下带水印留白）',
      },
      null,
      2
    )
  )
})()
