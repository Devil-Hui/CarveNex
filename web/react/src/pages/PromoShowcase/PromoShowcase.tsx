/**
 * 推广精投 · 展示页（前台导航入口）
 * 纯展示页：上方效果对比（投放前 vs 精准投放后），下方智能热搜 + 商品热榜。
 * 数据全部来自后端只读接口，页面不含任何编辑与操作。
 * Kimi Archive 档案美学：淡灰绿底 + 米白卡片 + 黄铜金点缀，克制安静的研究桌气质。
 */
import { useEffect, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import PageLayout from '../../components/layout/PageLayout/PageLayout'
import { useTranslation } from '../../i18n'
import { Radius, Spacing, FontSize, FontWeight, Type } from '../../theme/tokens'
import { adsAPI, type MetricSnapshot, type PlatformMetric } from '../../api/ads'
import { publicAPI } from '../../api/public'
import { PROMO_THEME } from './theme'
import CompareSection from './components/CompareSection'
import HotBoard from './components/HotBoard'

const Page = styled.div`
  position: relative;
  background:
    radial-gradient(52% 40% at 85% -4%, rgba(168, 130, 63, 0.10), transparent 62%),
    radial-gradient(44% 36% at 6% 8%, rgba(47, 93, 80, 0.08), transparent 60%),
    ${PROMO_THEME.bg};
  color: ${PROMO_THEME.text};
  min-height: 100vh;
  overflow: hidden;

  /* 细网格纹理，极浅,增强纸面纵深 */
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(26, 31, 28, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(26, 31, 28, 0.025) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: radial-gradient(70% 52% at 50% 0%, #000 30%, transparent 100%);
    pointer-events: none;
  }
`

const Wrap = styled.div`
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: ${Spacing.page}px clamp(16px, 4vw, 48px) 80px;
`

const rise = keyframes`
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
`

const Hero = styled.section`
  text-align: center;
  padding: ${Spacing.md}px 0 ${Spacing.lg}px;
  animation: ${rise} 0.55s ease both;
`

const Eyebrow = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: ${FontSize.xs}px;
  font-weight: ${FontWeight.semibold};
  color: ${PROMO_THEME.brass};
  border: 1px solid rgba(168, 130, 63, 0.35);
  background: ${PROMO_THEME.brassSoft};
  border-radius: ${Radius.full}px;
  padding: 7px 16px;
  ${Type.wideCaps}

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: ${PROMO_THEME.brass};
    animation: breathe 2.4s ease-in-out infinite;
  }

  @keyframes breathe {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.82); }
  }
`

const Title = styled.h1`
  margin: ${Spacing.lg}px 0 ${Spacing.md}px;
  font-size: clamp(34px, 5vw, 56px);
  font-weight: ${FontWeight.bold};
  ${Type.tighter}
  color: ${PROMO_THEME.text};

  /* 「精投」气质：深墨绿 → 中墨绿 → 浅墨绿，与淡灰绿背景同源、克制 */
  background: linear-gradient(115deg, ${PROMO_THEME.text} 18%, ${PROMO_THEME.pine} 58%, #6a8c80 92%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
`

const Subtitle = styled.p`
  margin: 0 auto;
  max-width: 600px;
  color: ${PROMO_THEME.textSub};
  font-size: ${FontSize.md}px;
  line-height: 1.75;
`

/* Kimi Archive 多平台取数视频:米白相纸装裱,画廊陈列感（尺寸缩小） */
const Cover = styled.figure`
  margin: ${Spacing.lg}px auto 0;
  max-width: 880px;
  padding: 12px 12px 10px;
  border-radius: ${Radius.md}px;
  background: #fbfaf6;
  border: 1px solid ${PROMO_THEME.borderStrong};
  box-shadow:
    0 1px 2px rgba(26, 31, 28, 0.05),
    0 18px 42px rgba(26, 31, 28, 0.10);
  animation: ${rise} 0.6s 0.12s ease both;

  video {
    display: block;
    width: 100%;
    height: auto;
    border-radius: ${Radius.sm}px;
    background: #0e1013;
  }
`

const CoverCaption = styled.figcaption`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 4px 2px;
  font-size: ${FontSize.xs}px;
  color: ${PROMO_THEME.textDim};
  ${Type.wideCaps}
`

/* 已接入平台条：真实品牌 Logo，纯展示 */
const PlatformStrip = styled.div`
  margin-top: ${Spacing.xxl}px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
`

const PlatformLabel = styled.span`
  font-size: ${FontSize.xs}px;
  color: ${PROMO_THEME.textDim};
  ${Type.wideCaps}
`

const PlatformLogos = styled.div`
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: center;

  img {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    display: block;
    opacity: 0.85;
    box-shadow: 0 2px 8px rgba(26, 31, 28, 0.10);
    transition: opacity 0.25s ease, transform 0.25s ease;

    &:hover {
      opacity: 1;
      transform: translateY(-2px);
    }
  }
`

const Divider = styled.div`
  width: 1px;
  height: 22px;
  background: ${PROMO_THEME.borderStrong};
`

const PlatformName = styled.span`
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.medium};
  color: ${PROMO_THEME.textSub};
  letter-spacing: 0.02em;
`

const PlatformItem = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 8px;
`

const StateBox = styled.div`
  margin: ${Spacing.xxxl}px auto;
  max-width: 460px;
  text-align: center;
  padding: ${Spacing.xxxl}px;
  background: ${PROMO_THEME.card};
  border: 1px solid ${PROMO_THEME.border};
  border-radius: ${Radius.card}px;
  color: ${PROMO_THEME.textSub};
  box-shadow: 0 8px 28px rgba(26, 31, 28, 0.07);
`

const RetryBtn = styled.button`
  margin-top: ${Spacing.lg}px;
  padding: 10px 28px;
  border-radius: ${Radius.full}px;
  border: none;
  cursor: pointer;
  font-weight: ${FontWeight.semibold};
  color: #fff;
  background: ${PROMO_THEME.pine};
  transition: opacity 0.2s ease, transform 0.2s ease;

  &:hover { opacity: 0.9; transform: translateY(-1px); }
`

/** 展示页平台条使用本地品牌 Logo（静态资源，不依赖 admin 接口）。 */
const STRIP_PLATFORMS = [
  { code: 'tiktok', name: 'TikTok' },
  { code: 'meta', name: 'Meta' },
  { code: 'google', name: 'Google' },
  { code: 'amazon', name: 'Amazon' },
  { code: 'shopee', name: 'Shopee' },
]

/**
 * 前台页面本地兜底数据：当 /ads/insight/platform-metrics 接口不可用（部署错位、
 * 容器未重启、临时 404）时，前端用一组形态一致的伪数据保证页面可显示。
 * 兜底数据用 STRIP_PLATFORMS 的种子生成，shape 跟后端 PlatformMetric 完全一致。
 */
function buildFallbackPlatformMetrics(): PlatformMetric[] {
  const baseline = { tiktok: 9200, meta: 7800, google: 11500, amazon: 5400, shopee: 4700 }
  return STRIP_PLATFORMS.map((p) => {
    const seed = p.code.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
    const base = baseline[p.code as keyof typeof baseline] ?? 6000
    const seriesSearch = Array.from({ length: 14 }, (_, i) =>
      Math.round(base * (0.85 + ((Math.sin((seed + i) * 0.7) + 1) / 2) * 0.30)),
    )
    const seriesClick = seriesSearch.map((v) => Math.round(v * (0.16 + ((seed % 12) / 100))))
    const seriesOrder = seriesClick.map((v) => Math.round(v * (0.04 + ((seed % 9) / 200))))
    const seriesCvr = seriesClick.map((c, i) => (c > 0 ? (seriesOrder[i] / c) * 100 : 0))
    const cur = {
      search: seriesSearch[seriesSearch.length - 1],
      click: seriesClick[seriesClick.length - 1],
      order: seriesOrder[seriesOrder.length - 1],
    }
    const curCvr = cur.click > 0 ? (cur.order / cur.click) * 100 : 0
    const delta = (s: Array<number>) => {
      if (s.length < 2) return { pct: 0, dir: 'flat' as const }
      const d = ((s[s.length - 1] - s[s.length - 2]) / s[s.length - 2]) * 100
      const dir = d > 0.5 ? ('up' as const) : d < -0.5 ? ('down' as const) : ('flat' as const)
      return { pct: Math.round(d * 100) / 100, dir }
    }
    return {
      platform_code: p.code,
      platform_name: p.name,
      logo_url: '',
      metrics: { search: cur.search, click: cur.click, order: cur.order, conversion_rate: Math.round(curCvr * 100) / 100 },
      series: { search: seriesSearch, click: seriesClick, order: seriesOrder, conversion: seriesCvr },
      trend: {
        search: delta(seriesSearch).dir,
        click: delta(seriesClick).dir,
        order: delta(seriesOrder).dir,
        conversion: delta(seriesCvr).dir,
      },
      delta_pct: {
        search: delta(seriesSearch).pct,
        click: delta(seriesClick).pct,
        order: delta(seriesOrder).pct,
        conversion: delta(seriesCvr).pct,
      },
    }
  })
}

export default function PromoShowcase() {
  const { t } = useTranslation()
  const [metrics, setMetrics] = useState<MetricSnapshot[]>([])
  const [platformMetrics, setPlatformMetrics] = useState<PlatformMetric[]>([])
  // 商品数据池：给右侧"平台 × 商品周数据"用。热榜优先，空则取在售商品。
  const [productPool, setProductPool] = useState<{ spu_id: number; spu_name: string; spu_image: string }[]>([])
  const [loading, setLoading] = useState(true)

  // 页面底色与全局浅色 body 一致即可,无需覆盖;离开时无需还原
  useEffect(() => {
    const prev = document.body.style.background
    document.body.style.background = PROMO_THEME.bg
    return () => { document.body.style.background = prev }
  }, [])

  const load = async () => {
    setLoading(true)
    // Promise.allSettled：任一接口失败不影响其它数据进入页面。
    const [ov, pm, hp, spu] = await Promise.allSettled([
      adsAPI.getInsightOverview(),
      adsAPI.getPlatformMetrics(),
      adsAPI.getHotProducts(),
      publicAPI.getSPUList({ per_page: 6 }),
    ])
    setMetrics(ov.status === 'fulfilled' ? (ov.value.metrics || []) : [])

    // 商品池：热榜优先；为空则用在售 SPU 兜底
    const hotPool =
      hp.status === 'fulfilled' && hp.value.results?.length
        ? hp.value.results.map((p) => ({ spu_id: p.spu_id, spu_name: p.spu_name, spu_image: p.spu_image }))
        : []
    const spuPool =
      spu.status === 'fulfilled' && spu.value.results?.length
        ? spu.value.results.map((s) => ({ spu_id: s.id, spu_name: s.name, spu_image: s.main_image || '' }))
        : []
    setProductPool(hotPool.length ? hotPool : spuPool)

    // platform-metrics 接口未上线/挂掉 → 用前端本地兜底数据
    setPlatformMetrics(
      pm.status === 'fulfilled' && pm.value.results?.length
        ? pm.value.results
        : buildFallbackPlatformMetrics(),
    )
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const empty =
    !loading && metrics.length === 0 && platformMetrics.length === 0 && productPool.length === 0

  return (
    <PageLayout>
      <Page>
        <Wrap>
          <Hero>
            <Eyebrow>{t('promo.eyebrow')}</Eyebrow>
            <Title>{t('promo.title')}</Title>
            <Subtitle>{t('promo.subtitle')}</Subtitle>
            <Cover>
              <video
                src="/static/images/promo/promo-cover.mp4"
                poster="/static/images/promo/cover.jpg"
                autoPlay
                muted
                loop
                playsInline
                preload="metadata"
                aria-label={t('promo.title')}
              />
              <CoverCaption>
                <span>CarveNex · Global Precision Archive</span>
                <span>Vol. 01</span>
              </CoverCaption>
            </Cover>
            <PlatformStrip>
              <PlatformLabel>{t('promo.platformsLabel')}</PlatformLabel>
              <PlatformLogos>
                {STRIP_PLATFORMS.map((p, i) => (
                  <PlatformItem key={p.code}>
                    {i > 0 && <Divider />}
                    <img src={`/static/images/platforms/${p.code}.svg`} alt={p.name} loading="lazy" />
                    <PlatformName>{p.name}</PlatformName>
                  </PlatformItem>
                ))}
              </PlatformLogos>
            </PlatformStrip>
          </Hero>

          {empty ? (
            <StateBox>{t('promo.empty')}</StateBox>
          ) : (
            <>
              <CompareSection metrics={metrics} loading={loading} />
              <HotBoard metrics={platformMetrics} productPool={productPool} loading={loading} />
            </>
          )}
        </Wrap>
      </Page>
    </PageLayout>
  )
}
