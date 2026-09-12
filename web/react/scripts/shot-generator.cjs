/* AI 生成面板三态截图：配置 → 生成中（模糊蒙版+清单） → 完成（清晰+三视图） */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto('http://localhost:12700/', { waitUntil: 'load', timeout: 60000 })

  const panel = page.locator('#use-cases')
  await panel.scrollIntoViewIfNeeded()
  await page.waitForTimeout(1200)

  // 配置：选材质 Metal、场景 Gifts、填写诉求（作用域限定在面板内，画廊有同名 chip）
  await panel.getByRole('button', { name: 'Metal', exact: true }).click()
  await panel.getByRole('button', { name: 'Gifts', exact: true }).click()
  await panel.locator('textarea').fill('A brass coin with our wedding date')
  await page.waitForTimeout(400)
  await page.screenshot({ path: 'scripts/shots/gen-1-config.png' })

  // 生成中：捕捉模糊蒙版 + 清单逐条完成
  await panel.getByRole('button', { name: 'Generate Preview' }).click()
  await page.waitForTimeout(3200)
  await page.screenshot({ path: 'scripts/shots/gen-2-generating.png' })

  // 完成：清晰 + 三视图
  await page.waitForTimeout(4500)
  await page.screenshot({ path: 'scripts/shots/gen-3-done.png' })

  await browser.close()
  console.log('OK')
})().catch((e) => {
  console.error('FAIL:', e.message)
  process.exit(1)
})
