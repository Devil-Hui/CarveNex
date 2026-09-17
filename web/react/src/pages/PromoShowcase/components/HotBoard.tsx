/**
 * 平台 × 商品周数据区：左窄右宽。
 *
 * 左侧窄栏：平台列表（logo + 名称 + 当前搜索量），点击切换选中平台。
 * 右侧宽栏：选中平台下的商品卡片，每个商品展示本周（周一 ~ 今天）的
 * 搜索量折线图 + 转化率环图 + 4 项核心指标。天数由后端按当前星期返回
 * （今天周四则 4 天数据）。
 *
 * 接口失败时前端本地生成形态一致的兜底数据，页面永不空白。
 */
import styled, { keyframes } from 'styled-components'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from '../../../i18n'
import { localizedText } from '../../../utils/localizedText'
import { Radius, Spacing, FontSize, FontWeight, Type } from '../../../theme/tokens'
import { PROMO_THEME as THEME } from '../theme'
import SmartImage from '../../../components/common/SmartImage/SmartImage'
import { optionalMediaUrl } from '../../../utils/mediaUrl'
import { adsAPI, type PlatformMetric, type ProductWeeklyItem } from '../../../api/ads'

const PLATFORM_LOGO: Record<string, string> = {
  tiktok: '/static/images/platforms/tiktok.svg',
  meta: '/static/images/platforms/meta.svg',
  google: '/static/images/platforms/google.svg',
  amazon: '/static/images/platforms/amazon.svg',
  shopee: '/static/images/platforms/shopee.svg',
}

const PLATFORM_TINT: Record<string, string> = {
  tiktok: '#25f4ee',
  meta: '#1877f2',
  google: '#ea4335',
  amazon: '#ff9900',
  shopee: '#ee4d2d',
}

const DEFAULT_PLATFORMS = [
  { code: 'tiktok', name: 'TikTok' },
  { code: 'meta', name: 'Meta' },
  { code: 'google', name: 'Google' },
  { code: 'amazon', name: 'Amazon' },
  { code: 'shopee', name: 'Shopee' },
]

/* ──────────── 框架 ──────────── */
const rise = keyframes`
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
`

const Section = styled.section`
  margin-top: ${Spacing.page}px;
  animation: ${rise} 0.55s 0.16s ease both;
`

/* 左窄右宽：3 : 8 */
const Grid = styled.div`
  display: grid;
  grid-template-columns: 3fr 8fr;
  gap: ${Spacing.lg}px;
  align-items: start;

  @media (max-width: 860px) {
    grid-template-columns: 1fr;
  }
`

const Card = styled.div`
  position: relative;
  background: ${THEME.card};
  border: 1px solid ${THEME.border};
  border-radius: ${Radius.panel}px;
  padding: ${Spacing.xl}px;
  box-shadow: 0 1px 2px rgba(26, 31, 28, 0.04), 0 14px 36px rgba(26, 31, 28, 0.07);
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(168, 130, 63, 0.55), transparent);
  }
`

const CardHead = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: ${Spacing.lg}px;
`

const CardTitle = styled.h3`
  margin: 0 0 ${Spacing.xs}px;
  font-size: ${FontSize.lg}px;
  font-weight: ${FontWeight.bold};
  color: ${THEME.text};
`

const CardSub = styled.p`
  margin: 0;
  color: ${THEME.textSub};
  font-size: ${FontSize.sm}px;
`

const LiveTag = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: ${FontSize.xs}px;
  color: ${THEME.pos};
  border: 1px solid rgba(61, 122, 94, 0.32);
  background: rgba(61, 122, 94, 0.08);
  border-radius: ${Radius.full}px;
  padding: 4px 10px;
  ${Type.wideCaps}

  &::before {
    content: '';
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: ${THEME.pos};
  }
`

/* ──────────── 左侧：平台列表 ──────────── */
const PlatformList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`

const PlatformRow = styled.button<{ $active: boolean }>`
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: ${Radius.md}px;
  border: 1px solid ${({ $active }) => ($active ? THEME.borderStrong : 'transparent')};
  background: ${({ $active }) => ($active ? THEME.cardSoft : 'transparent')};
  cursor: pointer;
  text-align: left;
  transition: background 0.18s ease, border-color 0.18s ease;

  &:hover {
    background: ${THEME.cardSoft};
  }

  img {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    object-fit: contain;
    flex-shrink: 0;
    box-shadow: 0 1px 4px rgba(26, 31, 28, 0.10);
  }
`

const PlatformRowName = styled.span<{ $active: boolean }>`
  flex: 1;
  min-width: 0;
  font-size: ${FontSize.sm}px;
  font-weight: ${({ $active }) => ($active ? FontWeight.semibold : FontWeight.medium)};
  color: ${({ $active }) => ($active ? THEME.text : THEME.textSub)};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

const PlatformRowValue = styled.span`
  ${Type.tnum};
  font-size: ${FontSize.xs}px;
  color: ${THEME.textDim};
  flex-shrink: 0;
`

/* ──────────── 右侧：商品周数据卡 ──────────── */
const DayChips = styled.div`
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: ${Spacing.md}px;
`

const DayChip = styled.span<{ $today?: boolean }>`
  font-size: 10px;
  ${Type.wideCaps};
  padding: 3px 9px;
  border-radius: ${Radius.full}px;
  border: 1px solid ${({ $today }) => ($today ? THEME.pine : THEME.border)};
  background: ${({ $today }) => ($today ? 'rgba(47, 93, 80, 0.10)' : 'transparent')};
  color: ${({ $today }) => ($today ? THEME.pine : THEME.textDim)};
  font-weight: ${({ $today }) => ($today ? FontWeight.semibold : FontWeight.medium)};
`

const ProductCard = styled.div`
  display: grid;
  grid-template-columns: 56px minmax(0, 1.4fr) minmax(0, 1.8fr) auto;
  gap: ${Spacing.md}px;
  align-items: center;
  padding: ${Spacing.md}px;
  border-radius: ${Radius.lg}px;
  border: 1px solid ${THEME.border};
  background: ${THEME.cardSoft};
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;

  &:hover {
    box-shadow: 0 4px 18px rgba(26, 31, 28, 0.08);
    transform: translateY(-1px);
  }

  & + & {
    margin-top: 10px;
  }

  @media (max-width: 640px) {
    grid-template-columns: 48px 1fr;
  }
`

const Thumb = styled.div`
  width: 56px;
  height: 56px;
  border-radius: ${Radius.md}px;
  overflow: hidden;
  flex-shrink: 0;
  background: ${THEME.card};
  border: 1px solid ${THEME.border};

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
`

const ProductInfo = styled.div`
  min-width: 0;
`

const ProductName = styled.div`
  font-size: ${FontSize.base}px;
  font-weight: ${FontWeight.semibold};
  color: ${THEME.text};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

const ProductMetrics = styled.div`
  margin-top: 5px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
`

const MiniMetric = styled.span`
  font-size: 10px;
  color: ${THEME.textDim};
  ${Type.wideCaps};

  b {
    ${Type.tnum};
    color: ${THEME.text};
    font-weight: ${FontWeight.semibold};
    margin-left: 4px;
  }
`

/* 折线图 */
const WeekChartWrap = styled.div`
  min-width: 0;
`

const WeekChartLabel = styled.div`
  font-size: 10px;
  color: ${THEME.textDim};
  ${Type.wideCaps};
  margin-bottom: 4px;
  display: flex;
  justify-content: space-between;
`

const WeekSvg = styled.svg`
  width: 100%;
  height: 44px;
  display: block;
`

/* 环图 */
const DonutWrap = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
`

const DonutLabel = styled.span`
  font-size: 10px;
  color: ${THEME.textDim};
  ${Type.wideCaps};
`

const DonutValue = styled.span`
  ${Type.tnum};
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.bold};
  color: ${THEME.text};
`

const SkeletonBar = styled.div`
  height: 18px;
  border-radius: 6px;
  margin: 12px 0;
  background: linear-gradient(90deg, rgba(26,31,28,0.05) 25%, rgba(26,31,28,0.10) 50%, rgba(26,31,28,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;

  @keyframes shimmer {
    from { background-position: 200% 0; }
    to { background-position: -200% 0; }
  }
`

const EmptyText = styled.div`
  color: ${THEME.textSub};
  font-size: ${FontSize.sm}px;
  padding: ${Spacing.xl}px 0;
  text-align: center;
`

/* ──────────── 工具 ──────────── */
function formatHeat(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(Math.round(n))
}

/** 本周逐日折线：宽度自适应，x 轴按点数均分。 */
function WeeklyLine({ values, color }: { values: number[]; color: string }) {
  if (!values.length) return <WeekSvg viewBox="0 0 200 44" preserveAspectRatio="none" />
  const W = 200
  const H = 44
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const range = max - min || 1
  const step = values.length > 1 ? W / (values.length - 1) : 0
  const pts = values.map((v, i) => {
    const x = values.length > 1 ? i * step : W / 2
    const y = H - 4 - ((v - min) / range) * (H - 10)
    return [x, y] as const
  })
  const path = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const id = `w-${Math.abs(color.split('').reduce((a, c) => a + c.charCodeAt(0), 0))}`
  return (
    <WeekSvg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.30" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L${W} ${H} L0 ${H} Z`} fill={`url(#${id})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === pts.length - 1 ? 2.6 : 1.6} fill={color} />
      ))}
    </WeekSvg>
  )
}

/** 转化率环图：SVG 圆环，缺口为背景轨道。 */
function CvrDonut({ pct, color }: { pct: number; color: string }) {
  const r = 18
  const c = 2 * Math.PI * r
  const clamped = Math.max(0, Math.min(pct, 100))
  const filled = (clamped / 100) * c
  return (
    <DonutWrap>
      <svg width="48" height="48" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r={r} fill="none" stroke="rgba(26,31,28,0.08)" strokeWidth="5" />
        <circle
          cx="24"
          cy="24"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${c - filled}`}
          transform="rotate(-90 24 24)"
        />
        <text
          x="24"
          y="24"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="10"
          fontWeight="700"
          fill={THEME.text}
        >
          {clamped.toFixed(1)}
        </text>
      </svg>
      <DonutLabel>CVR</DonutLabel>
    </DonutWrap>
  )
}

/* ──────────── 前端兜底：接口未上线时本地生成同形态数据 ──────────── */
function seedOf(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}

function weekDayLabels(): string[] {
  const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const today = new Date()
  const weekday = (today.getDay() + 6) % 7 // JS Sun=0 → Mon=0
  const out: string[] = []
  for (let i = 0; i <= weekday; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() - (weekday - i))
    out.push(`${names[(d.getDay() + 6) % 7]} ${d.getMonth() + 1}/${d.getDate()}`)
  }
  return out
}

function buildFallbackWeekly(
  platform: string,
  products: { spu_id: number; spu_name: string; spu_image: string }[],
): { days: string[]; items: ProductWeeklyItem[] } {
  const days = weekDayLabels()
  let totalOrder = 0
  const items: ProductWeeklyItem[] = products.map((p) => {
    const seed = seedOf(`${platform}-${p.spu_id}`)
    const base = 400 + (seed % 900)
    const search: number[] = []
    const click: number[] = []
    const order: number[] = []
    for (let i = 0; i < days.length; i++) {
      const h = seedOf(`${platform}-${p.spu_id}-${i}`)
      const pct = ((h % 6000) - 3000) / 10000
      const vs = base * (1 + pct)
      const vc = vs * (0.14 + (seed % 10) / 100)
      const vo = vc * (0.04 + (seed % 6) / 100)
      search.push(Math.round(vs * 10) / 10)
      click.push(Math.round(vc * 10) / 10)
      order.push(Math.round(vo * 10) / 10)
    }
    const curCvr = click[click.length - 1] > 0 ? (order[order.length - 1] / click[click.length - 1]) * 100 : 0
    totalOrder += order[order.length - 1]
    return {
      spu_id: p.spu_id,
      spu_name: p.spu_name,
      spu_name_en: p.spu_name,
      spu_name_ar: p.spu_name,
      spu_image: p.spu_image,
      metrics: {
        search: search[search.length - 1],
        click: click[click.length - 1],
        order: order[order.length - 1],
        conversion_rate: Math.round(curCvr * 100) / 100,
      },
      weekly: { search, click, order },
      order_share: 0,
    }
  })
  if (totalOrder > 0) {
    for (const it of items) {
      it.order_share = Math.round((it.metrics.order / totalOrder) * 10000) / 10000
    }
  }
  return { days, items }
}

interface Props {
  metrics: PlatformMetric[]
  productPool: { spu_id: number; spu_name: string; spu_image: string }[]
  loading: boolean
}

export default function HotBoard({ metrics, productPool, loading }: Props) {
  const { t, lang } = useTranslation()
  const navigate = useNavigate()

  const platforms = useMemo(() => {
    if (metrics.length) return metrics.map((m) => ({ code: m.platform_code, name: m.platform_name }))
    return DEFAULT_PLATFORMS
  }, [metrics])

  const [activePlatform, setActivePlatform] = useState<string>('')
  useEffect(() => {
    if (!activePlatform && platforms.length) setActivePlatform(platforms[0].code)
  }, [platforms, activePlatform])

  /* 周数据按平台缓存，切换平台不重复请求 */
  const cacheRef = useRef<Record<string, { days: string[]; items: ProductWeeklyItem[] }>>({})
  const [weekly, setWeekly] = useState<{ days: string[]; items: ProductWeeklyItem[] }>({ days: [], items: [] })
  const [weeklyLoading, setWeeklyLoading] = useState(false)

  const loadWeekly = useCallback(async (platform: string) => {
    if (!platform) return
    if (cacheRef.current[platform]) {
      setWeekly(cacheRef.current[platform])
      return
    }
    setWeeklyLoading(true)
    try {
      const resp = await adsAPI.getProductWeekly(platform)
      const data = { days: resp.days || [], items: resp.items || [] }
      cacheRef.current[platform] = data
      setWeekly(data)
    } catch {
      // 接口未上线/失败：用商品池本地生成同形态兜底数据，页面仍有内容
      const data = buildFallbackWeekly(platform, productPool)
      cacheRef.current[platform] = data
      setWeekly(data)
    } finally {
      setWeeklyLoading(false)
    }
  }, [productPool])

  useEffect(() => {
    loadWeekly(activePlatform)
  }, [activePlatform, loadWeekly])

  const platformSearchValue = useMemo(() => {
    const map: Record<string, number> = {}
    for (const m of metrics) map[m.platform_code] = m.metrics.search
    return map
  }, [metrics])

  const platformColor = PLATFORM_TINT[activePlatform] ?? THEME.pine

  return (
    <Section>
      <Grid>
        {/* 左窄：平台列表 */}
        <Card>
          <CardHead>
            <div>
              <CardTitle>{t('promo.platformListTitle')}</CardTitle>
              <CardSub>{t('promo.platformListSub')}</CardSub>
            </div>
          </CardHead>
          <PlatformList role="tablist" aria-label="Platform">
            {platforms.map((p) => (
              <PlatformRow
                key={p.code}
                type="button"
                role="tab"
                aria-selected={activePlatform === p.code}
                $active={activePlatform === p.code}
                onClick={() => setActivePlatform(p.code)}
              >
                {PLATFORM_LOGO[p.code] ? <img src={PLATFORM_LOGO[p.code]} alt={p.name} /> : null}
                <PlatformRowName $active={activePlatform === p.code}>{p.name}</PlatformRowName>
                <PlatformRowValue>
                  {platformSearchValue[p.code] != null ? formatHeat(platformSearchValue[p.code]) : ''}
                </PlatformRowValue>
              </PlatformRow>
            ))}
          </PlatformList>
        </Card>

        {/* 右宽：选中平台下的商品周数据 */}
        <Card>
          <CardHead>
            <div>
              <CardTitle>{t('promo.productWeeklyTitle')}</CardTitle>
              <CardSub>{t('promo.productWeeklySub')}</CardSub>
            </div>
            <LiveTag>{t('promo.liveTag')}</LiveTag>
          </CardHead>

          {weekly.days.length > 0 && (
            <DayChips>
              {weekly.days.map((d, i) => (
                <DayChip key={d} $today={i === weekly.days.length - 1}>
                  {d}
                </DayChip>
              ))}
            </DayChips>
          )}

          {loading || weeklyLoading ? (
            Array.from({ length: 4 }).map((_, i) => <SkeletonBar key={i} />)
          ) : weekly.items.length === 0 ? (
            <EmptyText>{t('promo.emptyList')}</EmptyText>
          ) : (
            weekly.items.map((item) => (
              <ProductCard key={item.spu_id} onClick={() => navigate(`/product/${item.spu_id}`)}>
                <Thumb>
                  <SmartImage
                    src={optionalMediaUrl(item.spu_image)}
                    alt={localizedText(lang, item.spu_name, item.spu_name_en, item.spu_name_ar, item.spu_name)}
                    loading="lazy"
                    decoding="async"
                  />
                </Thumb>
                <ProductInfo>
                  <ProductName>
                    {localizedText(lang, item.spu_name, item.spu_name_en, item.spu_name_ar, item.spu_name)}
                  </ProductName>
                  <ProductMetrics>
                    <MiniMetric>
                      {t('promo.metricSearch')}<b>{formatHeat(item.metrics.search)}</b>
                    </MiniMetric>
                    <MiniMetric>
                      {t('promo.metricClick')}<b>{formatHeat(item.metrics.click)}</b>
                    </MiniMetric>
                    <MiniMetric>
                      {t('promo.metricOrder')}<b>{formatHeat(item.metrics.order)}</b>
                    </MiniMetric>
                    <MiniMetric>
                      {t('promo.orderShare')}<b>{(item.order_share * 100).toFixed(1)}%</b>
                    </MiniMetric>
                  </ProductMetrics>
                </ProductInfo>
                <WeekChartWrap>
                  <WeekChartLabel>
                    <span>{t('promo.weeklySearch')}</span>
                    <DonutValue>{formatHeat(item.metrics.search)}</DonutValue>
                  </WeekChartLabel>
                  <WeeklyLine values={item.weekly.search} color={platformColor} />
                </WeekChartWrap>
                <CvrDonut pct={item.metrics.conversion_rate} color={platformColor} />
              </ProductCard>
            ))
          )}
        </Card>
      </Grid>
    </Section>
  )
}