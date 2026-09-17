/* 首页视频画廊截图验证：滚动态 → 聚焦态 → 展开态 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => m.type() === 'error' && errors.push(`console: ${m.text()}`))

  await page.goto('http://localhost:12700/', { waitUntil: 'load', timeout: 60000 })
  await page.waitForTimeout(2500)

  const section = page.locator('section[aria-label="Real-World Scenarios"]')
  await section.scrollIntoViewIfNeeded()
  await page.waitForTimeout(6000)
  await page.screenshot({ path: 'scripts/shots/gallery-1-marquee.png' })

  // 聚焦态：点击第一行第一张卡片（dispatchEvent 绕过动画位移/视口检测）
  await section.locator('[data-track] button').first().dispatchEvent('click')
  await page.waitForTimeout(900)
  await page.screenshot({ path: 'scripts/shots/gallery-2-focus.png' })

  // 展开态：点击「Expand」
  await page.getByRole('button', { name: 'Expand' }).click()
  await page.waitForTimeout(900)
  await page.screenshot({ path: 'scripts/shots/gallery-3-expand.png' })

  // 播放态：点击网格第一张卡片
  await page.locator('div[role="dialog"] button[title]').first().click()
  await page.waitForTimeout(1500)
  await page.screenshot({ path: 'scripts/shots/gallery-4-player.png' })

  console.log('errors:', errors.length ? errors.slice(0, 8) : 'none')
  await browser.close()
})().catch((e) => {
  console.error('FAIL:', e.message)
  process.exit(1)
})
