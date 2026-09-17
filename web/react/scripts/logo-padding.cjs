// 分析 logo.png：背景色 + 非背景（可见图案）包围盒
const { chromium } = require('@playwright/test')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto('http://localhost:12700/', { waitUntil: 'domcontentloaded' })

  const result = await page.evaluate(async () => {
    const img = new Image()
    img.src = '/static/images/logo.png'
    await img.decode()

    const W = img.naturalWidth, H = img.naturalHeight
    const c = document.createElement('canvas')
    c.width = W; c.height = H
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0)
    const { data } = ctx.getImageData(0, 0, W, H)

    const px = (x, y) => {
      const i = (y * W + x) * 4
      return [data[i], data[i + 1], data[i + 2], data[i + 3]]
    }
    const corners = {
      topLeft: px(0, 0), topRight: px(W - 1, 0),
      bottomLeft: px(0, H - 1), bottomRight: px(W - 1, H - 1),
    }

    // 以左上角像素为背景基准，容差 22
    const [br, bg, bb] = corners.topLeft
    const near = (r, g, b, tol) =>
      Math.abs(r - br) <= tol && Math.abs(g - bg) <= tol && Math.abs(b - bb) <= tol

    let minX = W, minY = H, maxX = -1, maxY = -1
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 4
        const a = data[i + 3]
        if (a <= 8) continue
        if (near(data[i], data[i + 1], data[i + 2], 22)) continue
        if (x < minX) minX = x
        if (x > maxX) maxX = x
        if (y < minY) minY = y
        if (y > maxY) maxY = y
      }
    }
    if (maxX < 0) return { corners, note: '整图都是背景色，找不到图案' }

    const boxW = maxX - minX + 1, boxH = maxY - minY + 1
    return {
      corners,
      artworkBox: boxW + 'x' + boxH,
      artworkOffset: `left=${minX} top=${minY}`,
      artworkPercentOfCanvas: ((boxW / W) * 100).toFixed(1) + '% 宽 / ' + ((boxH / H) * 100).toFixed(1) + '% 高',
      at60px: `图案实际只画 ${Math.round((60 * boxW) / W)}x${Math.round((60 * boxH) / H)} px`,
      at80px: `图案实际只画 ${Math.round((80 * boxW) / W)}x${Math.round((80 * boxH) / H)} px`,
    }
  })

  console.log(JSON.stringify(result, null, 2))
  await browser.close()
})()
