// 临时校验：确认 header 中 logo img 的渲染尺寸为 80x80
const { chromium } = require('@playwright/test')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto('http://localhost:12700/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(3500)

  const info = await page.evaluate(() => {
    const img = document.querySelector('header > div:nth-child(2) > div:nth-child(1) > img')
    if (!img) {
      const all = [...document.querySelectorAll('header img')].map(
        (e) => e.getAttribute('src') + ' | ' + e.getBoundingClientRect().width + 'x' + e.getBoundingClientRect().height
      )
      return { found: false, headerImgs: all }
    }
    const r = img.getBoundingClientRect()
    const cs = getComputedStyle(img)
    return {
      found: true,
      src: img.getAttribute('src'),
      alt: img.getAttribute('alt'),
      rendered: Math.round(r.width) + 'x' + Math.round(r.height),
      cssWidth: cs.width,
      cssHeight: cs.height,
      objectFit: cs.objectFit,
    }
  })
  console.log(JSON.stringify(info, null, 2))

  await page.screenshot({ path: 'scripts/shots/logo-current.png', clip: { x: 0, y: 0, width: 1440, height: 220 } })
  await browser.close()
})()
