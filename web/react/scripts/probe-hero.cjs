/* 检测 Hero 视频在浏览器中的真实播放状态 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto('http://localhost:12700/', { waitUntil: 'load', timeout: 60000 })
  await page.waitForTimeout(5000)

  const info = await page.evaluate(() => {
    const v = document.querySelector('figure video')
    if (!v) return { found: false }
    return {
      found: true,
      src: v.currentSrc || v.src,
      readyState: v.readyState, // 0-4
      networkState: v.networkState,
      paused: v.paused,
      currentTime: v.currentTime,
      duration: v.duration,
      videoWidth: v.videoWidth,
      videoHeight: v.videoHeight,
      error: v.error ? { code: v.error.code, message: v.error.message } : null,
      canPlayAv1: document.createElement('video').canPlayType('video/mp4; codecs="av01.0.05M.08"'),
    }
  })
  console.log(JSON.stringify(info, null, 2))

  await page.locator('figure').first().scrollIntoViewIfNeeded()
  await page.waitForTimeout(500)
  await page.screenshot({ path: 'scripts/shots/hero-probe.png' })
  await browser.close()
})().catch((e) => {
  console.error('FAIL:', e.message)
  process.exit(1)
})
