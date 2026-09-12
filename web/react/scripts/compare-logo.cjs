// 生成「裁切前 vs 裁切后」在同样 45x45 方框下的放大对比图
const { chromium } = require('@playwright/test')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ deviceScaleFactor: 8 })
  await page.goto('http://localhost:12700/', { waitUntil: 'domcontentloaded' })

  await page.evaluate(async () => {
    // 预加载两张图，确保截图时已解码完成
    const load = (src) =>
      new Promise((res) => {
        const i = new Image()
        i.onload = () => res(i)
        i.onerror = () => res(i)
        i.src = src
      })
    await Promise.all([load('/static/images/logo.png'), load('/static/images/logo-trimmed.png')])

    const box = (label, src) => `
      <div style="display:flex;flex-direction:column;align-items:center;gap:8px;font:12px/1.4 system-ui,sans-serif;color:#333">
        <div style="width:45px;height:45px;outline:1px solid #ff6b6b;outline-offset:0;display:flex;align-items:center;justify-content:center">
          <img src="${src}" style="width:45px;height:45px;object-fit:contain;display:block" />
        </div>
        <div>${label}</div>
      </div>`

    const wrap = document.createElement('div')
    wrap.id = '__cmp'
    wrap.style.cssText =
      'position:fixed;z-index:2147483647;left:0;top:0;background:#fff;padding:16px;display:flex;gap:28px;align-items:flex-start'
    wrap.innerHTML = box('裁切前<br>(45px 方框)', '/static/images/logo.png') + box('裁切后<br>(45px 方框)', '/static/images/logo-trimmed.png')
    document.body.appendChild(wrap)
  })

  await page.waitForTimeout(600)
  await page.locator('#__cmp').screenshot({ path: 'scripts/shots/logo-compare.png' })
  await browser.close()
  console.log('已生成 scripts/shots/logo-compare.png')
})()
