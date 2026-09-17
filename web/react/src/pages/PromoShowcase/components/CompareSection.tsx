/**
 * 效果对比区：左侧灰度降饱和展示投放前，右侧黄铜金描边高亮展示精准投放后，中间箭头连接。
 * 每个指标带迷你数值条（以两侧最大值为满刻度）；CPC 等「越低越好」指标下降为正向（绿色徽章）。
 */
import { useEffect, useRef, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import { useTranslation } from '../../../i18n'
import { Radius, Spacing, FontSize, FontWeight, Type } from '../../../theme/tokens'
import { PROMO_THEME as THEME } from '../theme'
import type { MetricSnapshot } from '../../../api/ads'

const rise = keyframes`
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
`

const Section = styled.section`
  animation: ${rise} 0.55s 0.08s ease both;
`

const SectionHead = styled.div`
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: ${Spacing.xl}px;
  flex-wrap: wrap;
`

const SectionTitle = styled.h2`
  margin: 0;
  font-size: ${FontSize.xxl}px;
  font-weight: ${FontWeight.bold};
  ${Type.tight}
  display: flex;
  align-items: center;
  gap: 12px;

  &::before {
    content: '';
    width: 4px;
    height: 22px;
    border-radius: 2px;
    background: linear-gradient(180deg, ${THEME.brass}, ${THEME.pine});
  }
`

const SectionHint = styled.span`
  color: ${THEME.textSub};
  font-size: ${FontSize.sm}px;
`

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr 72px 1fr;
  gap: ${Spacing.lg}px;
  align-items: stretch;

  @media (max-width: 860px) {
    grid-template-columns: 1fr;
  }
`

const Panel = styled.div<{ $dim?: boolean }>`
  border-radius: ${Radius.panel}px;
  padding: ${Spacing.xxl}px;

  ${({ $dim }) =>
    $dim
      ? `
        background: rgba(255, 255, 255, 0.55);
        border: 1px solid ${THEME.border};
        filter: grayscale(0.9) saturate(0.45);
        opacity: 0.62;
      `
      : `
        background: ${THEME.card};
        border: 1.5px solid rgba(168, 130, 63, 0.55);
        box-shadow: 0 2px 6px rgba(26, 31, 28, 0.04), 0 20px 48px rgba(168, 130, 63, 0.14);
      `}
`

const PanelTag = styled.div<{ $tone: 'before' | 'after' }>`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: ${FontSize.xs}px;
  font-weight: ${FontWeight.semibold};
  padding: 6px 14px;
  border-radius: ${Radius.full}px;
  margin-bottom: ${Spacing.lg}px;
  ${Type.wideCaps}
  color: ${({ $tone }) => ($tone === 'after' ? '#fbfaf6' : THEME.textSub)};
  background: ${({ $tone }) =>
    $tone === 'after' ? `linear-gradient(120deg, ${THEME.pine}, #6a8c80)` : 'rgba(26, 31, 28, 0.07)'};
`

const MetricRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: ${Spacing.md}px 0;

  & + & {
    border-top: 1px solid ${THEME.border};
  }
`

const MetricName = styled.span`
  color: ${THEME.textSub};
  font-size: ${FontSize.sm}px;
  flex-shrink: 0;
  min-width: 72px;
`

const MetricRight = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: flex-end;
  min-width: 0;
`

const MetricValue = styled.span<{ $strong?: boolean }>`
  ${Type.tnum}
  font-weight: ${FontWeight.bold};
  font-size: ${({ $strong }) => ($strong ? FontSize.xxl : FontSize.lg)}px;
  color: ${THEME.text};
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  white-space: nowrap;
`

const UnitSign = styled.span`
  font-size: ${FontSize.xs}px;
  color: ${THEME.textSub};
  font-weight: ${FontWeight.medium};
`

const BarTrack = styled.div`
  width: 86px;
  height: 5px;
  border-radius: 3px;
  background: rgba(26, 31, 28, 0.08);
  overflow: hidden;
  flex-shrink: 0;

  @media (max-width: 1100px) {
    display: none;
  }
`

const BarFill = styled.div<{ $pct: number; $tone: 'before' | 'after' }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  border-radius: 3px;
  background: ${({ $tone }) =>
    $tone === 'after' ? `linear-gradient(90deg, ${THEME.pine}, #6a8c80)` : 'rgba(26, 31, 28, 0.28)'};
  transition: width 1s cubic-bezier(0.22, 1, 0.36, 1);
`

const DeltaBadge = styled.span<{ $good: boolean }>`
  ${Type.tnum}
  font-size: ${FontSize.xs}px;
  font-weight: ${FontWeight.semibold};
  padding: 3px 10px;
  border-radius: ${Radius.full}px;
  white-space: nowrap;
  color: ${({ $good }) => ($good ? THEME.pos : THEME.accent)};
  background: ${({ $good }) => ($good ? 'rgba(61, 122, 94, 0.10)' : 'rgba(254, 44, 85, 0.08)')};
  border: 1px solid ${({ $good }) => ($good ? 'rgba(61, 122, 94, 0.32)' : 'rgba(254, 44, 85, 0.28)')};
`

const ArrowCol = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;

  @media (max-width: 860px) {
    transform: rotate(90deg);
    padding: 4px 0;
  }
`

const ArrowGlow = styled.div`
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, ${THEME.pine}, #6a8c80);
  box-shadow: 0 10px 26px rgba(47, 93, 80, 0.32);

  &::after {
    content: '';
    position: absolute;
    inset: -6px;
    border-radius: 50%;
    border: 1.5px solid rgba(168, 130, 63, 0.4);
    animation: ringPulse 2.2s ease-out infinite;
  }

  @keyframes ringPulse {
    0% { transform: scale(0.9); opacity: 0.9; }
    100% { transform: scale(1.5); opacity: 0; }
  }
`

const SkeletonBar = styled.div<{ $w?: string }>`
  height: 18px;
  width: ${({ $w }) => $w || '60%'};
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(26,31,28,0.05) 25%, rgba(26,31,28,0.10) 50%, rgba(26,31,28,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;

  @keyframes shimmer {
    from { background-position: 200% 0; }
    to { background-position: -200% 0; }
  }
`

/** 数字滚动动画：展示页指标从 0 递增至目标值，强化「提升」观感。 */
function useCountUp(target: number, durationMs = 900): number {
  const [value, setValue] = useState(0)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, durationMs])

  return value
}

function formatValue(raw: string, unit: string): string {
  const num = Number(raw)
  if (!Number.isFinite(num)) return raw
  const text = num >= 10000 ? num.toLocaleString('en-US') : num.toString()
  if (unit === '$') return `$${text}`
  if (unit === '%') return `${text}%`
  if (unit === 'x') return `${text}x`
  return text
}

function AnimatedValue({ raw, unit, strong }: { raw: string; unit: string; strong?: boolean }) {
  const num = Number(raw)
  const animated = useCountUp(Number.isFinite(num) ? num : 0)
  const display = Number.isFinite(num)
    ? (num >= 10000 ? Math.round(animated).toLocaleString('en-US') : animated.toFixed(2).replace(/\.?0+$/, ''))
    : raw
  return (
    <MetricValue $strong={strong}>
      {unit === '$' && <UnitSign>$</UnitSign>}
      {display}
      {unit === '%' && <UnitSign>%</UnitSign>}
      {unit === 'x' && <UnitSign>x</UnitSign>}
    </MetricValue>
  )
}

export default function CompareSection({ metrics, loading }: { metrics: MetricSnapshot[]; loading: boolean }) {
  const { t } = useTranslation()

  const renderRows = (side: 'before' | 'after') => {
    if (loading) {
      return Array.from({ length: 5 }).map((_, i) => (
        <MetricRow key={i}>
          <SkeletonBar $w="40%" />
          <SkeletonBar $w="30%" />
        </MetricRow>
      ))
    }
    return metrics.map((m) => {
      const change = m.change_pct
      const good = change == null ? true : m.lower_is_better ? change < 0 : change > 0
      const before = Number(m.before_value)
      const after = Number(m.after_value)
      const max = Math.max(before, after, 1)
      const pct = side === 'before'
        ? Math.max(6, Math.round((before / max) * 100))
        : Math.max(6, Math.round((after / max) * 100))
      return (
        <MetricRow key={m.metric_key}>
          <MetricName>{t(`promo.metrics.${m.metric_key}`)}</MetricName>
          <MetricRight>
            <BarTrack><BarFill $pct={pct} $tone={side} /></BarTrack>
            {side === 'before' ? (
              <MetricValue>{formatValue(m.before_value, m.unit)}</MetricValue>
            ) : (
              <>
                <MetricValue $strong>
                  <AnimatedValue raw={m.after_value} unit={m.unit} strong />
                </MetricValue>
                {change != null && (
                  <DeltaBadge $good={good}>
                    {change > 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
                  </DeltaBadge>
                )}
              </>
            )}
          </MetricRight>
        </MetricRow>
      )
    })
  }

  return (
    <Section>
      <SectionHead>
        <SectionTitle>{t('promo.compareTitle')}</SectionTitle>
        <SectionHint>{t('promo.compareHint')}</SectionHint>
      </SectionHead>
      <Grid>
        <Panel $dim>
          <PanelTag $tone="before">{t('promo.before')}</PanelTag>
          {renderRows('before')}
        </Panel>
        <ArrowCol>
          <ArrowGlow>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" y1="12" x2="20" y2="12" />
              <polyline points="13 5 20 12 13 19" />
            </svg>
          </ArrowGlow>
        </ArrowCol>
        <Panel>
          <PanelTag $tone="after">{t('promo.after')}</PanelTag>
          {renderRows('after')}
        </Panel>
      </Grid>
    </Section>
  )
}
