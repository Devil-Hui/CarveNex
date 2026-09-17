// 多阈值分析 logo.png 的内容包围盒，用于找出「只框住真实图案」的阈值
// （原图右下角有极淡的图库水印，低阈值会把它算进去 → 裁切后显得留白）
const { chromium } = require('@playwright/test')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto('http://localhost:12700/', { waitUntil: 'domcontentloaded' })

  const out = await page.evaluate(async () => {
    const img = new Image()
    img.src = '/static/images/logo.png'
    await img.decode()
    const W = img.naturalWidth, H = img.naturalHeight
    const c = document.createElement('canvas')
    c.width = W; c.height = H
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0)
    const { data } = ctx.getImageData(0, 0, W, H)

    const bg = [data[0], data[1], data[2]]

    const bboxAt = (tol) => {
      let minX = W, minY = H, maxX = -1, maxY = -1, count = 0
      for (let y = 0; y < H; y++) {
        for (let x = 0; x < W; x++) {
          const i = (y * W + x) * 4
          const d = Math.max(
            Math.abs(data[i] - bg[0]),
            Math.abs(data[i + 1] - bg[1]),
            Math.abs(data[i + 2] - bg[2])
          )
          if (d <= tol) continue
          count++
          if (x < minX) minX = x
          if (x > maxX) maxX = x
          if (y < minY) minY = y
          if (y > maxY) maxY = y
        }
      }
      if (maxX < 0) return null
      const w = maxX - minX + 1, h = maxY - minY + 1
      return {
        tol,
        box: `${w}x${h}`,
        offset: `left=${minX} top=${minY}`,
        pctOfCanvas: `${((w / W) * 100).toFixed(1)}% x ${((h / H) * 100).toFixed(1)}%`,
        pixels: count,
        aspect: (w / h).toFixed(4),
      }
    }

    return {
      background: `rgb(${bg.join(',')})`,
      canvas: `${W}x${H}`,
      thresholds: [6, 16, 24, 32, 48, 64, 96, 140].map(bboxAt).filter(Boolean),
    }
  })

  console.log(JSON.stringify(out, null, 2))
  await browser.close()
})()
