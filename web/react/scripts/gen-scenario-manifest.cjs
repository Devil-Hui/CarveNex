/**
 * 扫描「laserpeck 应用场景」文件夹，生成首页视频画廊数据清单。
 * 用法：node scripts/gen-scenario-manifest.cjs
 * 目录约定：一级文件夹 = 行（上行/下行），二级文件夹 = 分类，根目录散文件归入「精选实拍」。
 * 源目录 / 输出清单 / URL 前缀均取自 scenario-videos.config.cjs（唯一配置源，禁止另写死）。
 */
const fs = require('fs')
const path = require('path')

const {
  SCENARIO_VIDEO_DIR: SRC,
  SCENARIO_MANIFEST: OUT,
  SCENARIO_VIDEO_URL: BASE,
} = require('../scenario-videos.config.cjs')

const VIDEO_EXT = new Set(['.mp4', '.mov', '.webm', '.m4v'])

/** 分类展示名 + 一句话说明（英文，≤20 字符） */
const CATEGORY_META = {
  '材料(皮革）': { name: 'Leather', desc: 'Rich grain engraving' },
  '材料（塑料）': { name: 'Plastic', desc: 'Done in 10 seconds' },
  '材料（布料)': { name: 'Fabric', desc: 'Soft yet engravable' },
  '材料（木材）': { name: 'Wood', desc: 'Photo & deep carving' },
  '材料（玻璃）': { name: 'Glass', desc: 'Crisp frosted finish' },
  '材料（石板）': { name: 'Stone', desc: '3D relief on slate' },
  '雕刻材料（金属）': { name: 'Metal', desc: 'Deep & color marking' },
  '3D刻印': { name: '3D Embossing', desc: 'Layered true relief' },
  'logo刻印': { name: 'Logo', desc: 'Branding in seconds' },
  '杯子改造': { name: 'Tumblers', desc: 'Your mark, your cup' },
  '礼品定制': { name: 'Gifts', desc: 'One-of-a-kind gifts' },
  '衣服、饰品定制': { name: 'Apparel', desc: 'Custom wearables' },
  '鞋类刻印': { name: 'Shoes', desc: 'Step up your style' },
  __root__: { name: 'Featured', desc: 'All-in-one scenes' },
}

const ROW_META = {
  '分类1：雕刻材料': { id: 'materials', name: 'Materials' },
  '分类2：使用场景': { id: 'usecases', name: 'Applications' },
}

const slug = (s, i) =>
  s
    .toLowerCase()
    .replace(/\.[^.]+$/, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || `video-${i}`

const encodePath = (rel) =>
  rel
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/')

const rows = []
for (const rowDir of fs.readdirSync(SRC)) {
  const rowPath = path.join(SRC, rowDir)
  if (!fs.statSync(rowPath).isDirectory()) continue
  const rowMeta = ROW_META[rowDir] || {
    id: slug(rowDir, rows.length),
    name: rowDir.replace(/^分类\d+：/, ''),
  }
  const categories = []
  const rootVideos = []

  for (const entry of fs.readdirSync(rowPath)) {
    const entryPath = path.join(rowPath, entry)
    const stat = fs.statSync(entryPath)
    if (stat.isDirectory()) {
      const videos = fs
        .readdirSync(entryPath)
        .filter((f) => VIDEO_EXT.has(path.extname(f).toLowerCase()))
        .sort()
        .map((f, i) => ({
          id: slug(f, i),
          title: f.replace(/\.[^.]+$/, ''),
          url: `${BASE}/${encodePath(`${rowDir}/${entry}/${f}`)}`,
        }))
      if (!videos.length) continue
      const meta = CATEGORY_META[entry] || { name: entry, desc: '' }
      categories.push({ id: slug(entry, categories.length), name: meta.name, desc: meta.desc, videos })
    } else if (VIDEO_EXT.has(path.extname(entry).toLowerCase())) {
      rootVideos.push({
        id: slug(entry, rootVideos.length),
        title: entry.replace(/\.[^.]+$/, ''),
        url: `${BASE}/${encodePath(`${rowDir}/${entry}`)}`,
      })
    }
  }
  if (rootVideos.length) {
    const meta = CATEGORY_META.__root__
    categories.unshift({ id: 'featured', name: meta.name, desc: meta.desc, videos: rootVideos.sort((a, b) => a.id.localeCompare(b.id)) })
  }
  if (categories.length) rows.push({ id: rowMeta.id, name: rowMeta.name, categories })
}

const ts = `/**
 * 首页「应用场景视频画廊」数据清单 —— 由 scripts/gen-scenario-manifest.cjs 自动生成，请勿手改。
 * 视频源：public/videos/laserpeck 文件夹，由 Vite/nginx 静态服务到 ${BASE}/。
 */
export interface ScenarioVideo {
  id: string
  title: string
  url: string
}

export interface ScenarioCategory {
  id: string
  /** 分类展示名（≤20 字） */
  name: string
  /** 分类一句话说明（≤20 字） */
  desc: string
  videos: ScenarioVideo[]
}

export interface ScenarioRow {
  id: string
  /** 行展示名（上行=雕刻材料，下行=使用场景） */
  name: string
  categories: ScenarioCategory[]
}

export const SCENARIO_ROWS: ScenarioRow[] = ${JSON.stringify(rows, null, 2)}
`

fs.writeFileSync(OUT, ts, 'utf8')
const total = rows.reduce((n, r) => n + r.categories.reduce((m, c) => m + c.videos.length, 0), 0)
console.log(`OK: ${rows.length} rows, ${total} videos -> ${OUT}`)
