/* 检测画廊前若干视频的加载/播放状态 */
const { chromium } = require('playwright')
const { SCENARIO_VIDEO_URL } = require('../scenario-videos.config.cjs')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const bad = []
  page.on('response', (r) => {
    if (r.url().includes(SCENARIO_VIDEO_URL) && r.status() >= 400) bad.push(`${r.status()} ${r.url()}`)
  })
  await page.goto('http://localhost:12700/', { waitUntil: 'load', timeout: 60000 })
  const section = page.locator('section[aria-label="Real-World Scenarios"]')
  await section.scrollIntoViewIfNeeded()
  await page.waitForTimeout(6000)

  const info = await page.evaluate(() => {
    const sec = document.querySelector('section[aria-label="Real-World Scenarios"]')
    const vids = [...sec.querySelectorAll('[data-track] video')].slice(0, 10)
    return vids.map((v) => ({
      src: (v.currentSrc || v.src).split('/').pop().slice(0, 40),
      rs: v.readyState,
      paused: v.paused,
      t: +v.currentTime.toFixed(1),
      err: v.error ? v.error.code : null,
    }))
  })
  console.log(JSON.stringify(info, null, 1))
  console.log('bad responses:', bad.length ? bad.slice(0, 5) : 'none')
  await page.screenshot({ path: 'scripts/shots/gallery-probe.png' })
  await browser.close()
})().catch((e) => {
  console.error('FAIL:', e.message)
  process.exit(1)
})
