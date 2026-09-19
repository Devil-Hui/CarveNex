/**
 * 首页「应用场景视频画廊」唯一配置源（Single Source of Truth）
 * ═══════════════════════════════════════════════════════════════════
 * 视频统一存放于 web/react/public/videos/laserpeck/（唯一一份；
 * 原 public/videos/laser 的改名重复副本已删除），由 Vite（dev/preview）
 * 与 nginx（prod）直接静态服务——不再需要自定义中间件/额外卷挂载。
 *
 * 本文件定义：视频源目录、浏览器访问前缀、画廊清单输出——全项目只此一处。
 * 覆盖方式：环境变量 SCENARIO_VIDEO_DIR。
 */
const path = require('path')

/** 唯一视频源目录：public/videos/laserpeck（Vite public 静态目录，构建时进入 dist） */
const SCENARIO_VIDEO_DIR =
  process.env.SCENARIO_VIDEO_DIR || path.join(__dirname, 'public', 'videos', 'laserpeck')

/** 唯一 URL 前缀：视频已上传到 Cloudflare R2/CDN（cdn.carvenex.com），
 * 直接引用 CDN 绝对路径。前端部署在 Cloudflare Pages，同源 /videos/ 会命中
 * SPA fallback（返回 index.html 而非视频），故必须走 CDN。 */
const SCENARIO_VIDEO_URL = process.env.SCENARIO_VIDEO_URL || 'https://cdn.carvenex.com/videos/laserpeck'

/** 唯一画廊清单：由 gen-scenario-manifest.cjs 生成、ScenarioGallery.tsx 消费 */
const SCENARIO_MANIFEST = path.join(__dirname, 'src', 'pages', 'Home', 'data', 'scenarioGallery.ts')

module.exports = {
  SCENARIO_VIDEO_DIR,
  SCENARIO_VIDEO_URL,
  SCENARIO_MANIFEST,
}
