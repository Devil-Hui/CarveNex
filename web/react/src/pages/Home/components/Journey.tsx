import styled from 'styled-components'
import { Font, Ink, Radius, Type, cardSurface, gridContainer, Rhythm, mq } from '../editorial'
import { Reveal } from './Reveal'
import { FigureBox, SectionHead } from './ui/primitives'
import LaserVideo, { LASER_VIDEOS } from './ui/LaserVideo'
import { useTranslation } from '../../../i18n'

/* ── 資料 ─────────────────────────────────────────────────── */
const STEPS = [1, 2, 3, 4, 5, 6]

/* ── 區塊 ─────────────────────────────────────────────────── */
const Section = styled.section`
  padding-block: ${Rhythm.section};
  background: ${Ink.paperAlt};
  border-bottom: 1px solid ${Ink.rule};
`

const Grid12 = styled.div`
  ${gridContainer};
  row-gap: clamp(2rem, 5vw, 3rem);
`

const HeadRow = styled.div`
  grid-column: 1 / -1;
`

/* ── 左：六步驟（1px 細線連接） ──────────────────────────── */
const Layout = styled.div`
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr;
  gap: clamp(1.75rem, 4vw, 3rem);
  align-items: start;

  ${mq.mdUp} {
    grid-template-columns: minmax(0, 1fr) 360px;
  }
`

const Steps = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: 1fr;
  gap: 1rem;

  ${mq.lgUp} {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
`

const Step = styled.li`
  ${cardSurface};
  position: relative;
  height: 100%;
  border-radius: ${Radius.xl}px;
  padding: 1.25rem 1rem;
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.3s cubic-bezier(0.22, 1, 0.36, 1);

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(14, 16, 19, 0.08);
  }
`

const Num = styled.div`
  width: 34px;
  height: 34px;
  margin-bottom: 0.85rem;
  border-radius: ${Radius.sm}px;
  background: ${Ink.black};
  color: ${Ink.paper};
  font-family: ${Font.display};
  ${Type.tnum}
  font-size: 0.9rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
`

const StepTitle = styled.h3`
  font-family: ${Font.display};
  font-size: 0.95rem;
  font-weight: 700;
  ${Type.tight}
  color: ${Ink.black};
  margin: 0 0 0.35rem;
`

const StepDesc = styled.p`
  font-size: 0.78rem;
  line-height: 1.5;
  color: ${Ink.graphite};
  margin: 0;
`

/* ── 右：實拍圖 ───────────────────────────────────────────── */
const AsideFigure = styled.div`
  ${mq.mdUp} {
    position: sticky;
    top: 96px;
  }
`

export default function Journey() {
  const { t } = useTranslation()
  return (
    <Section id="journey">
      <Grid12>
        <HeadRow>
          <Reveal>
            <SectionHead
              eyebrow={t('store.landing.journey.eyebrow')}
              title={t('store.landing.journey.title')}
              lead={t('store.landing.journey.lead')}
            />
          </Reveal>
        </HeadRow>

        <Layout>
          <Steps>
            {STEPS.map((n) => (
              <Reveal key={n} delay={(n - 1) * 70}>
                <Step>
                  <Num>{n}</Num>
                  <StepTitle>{t(`store.landing.journey.steps.${n}.title`)}</StepTitle>
                  <StepDesc>{t(`store.landing.journey.steps.${n}.desc`)}</StepDesc>
                </Step>
              </Reveal>
            ))}
          </Steps>

          <Reveal delay={120}>
            <AsideFigure>
              <FigureBox
                label={t('store.landing.journey.figureLabel')}
                meta={t('store.landing.journey.figureMeta')}
                flush
              >
                <LaserVideo src={LASER_VIDEOS.lp1} ratio="4 / 3" />
              </FigureBox>
            </AsideFigure>
          </Reveal>
        </Layout>
      </Grid12>
    </Section>
  )
}
