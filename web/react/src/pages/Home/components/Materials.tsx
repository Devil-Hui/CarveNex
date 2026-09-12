import styled from 'styled-components'
import { Font, Ink, Radius, Type, cardSurface, gridContainer, Rhythm } from '../editorial'
import { Reveal } from './Reveal'
import { SectionHead } from './ui/primitives'
import LaserVideo, { LASER_VIDEOS } from './ui/LaserVideo'
import { IconArrowRight } from './ui/Icon'

/* ── 資料：七種雕刻材料 ─────────────────────────────────── */
const MATERIALS: { name: string; note: string; src: string }[] = [
  { name: 'Wood', note: 'Photo engraving & deep carving', src: LASER_VIDEOS.wood },
  { name: 'Metal', note: 'Logos, tags & photo embossing', src: LASER_VIDEOS.metal },
  { name: 'Glass', note: 'Frosted jars, cups & bottles', src: LASER_VIDEOS.glass },
  { name: 'Leather', note: 'Gifts, patches & small-batch goods', src: LASER_VIDEOS.leather },
  { name: 'Fabric', note: 'Towels, tees & apparel branding', src: LASER_VIDEOS.fabric },
  { name: 'Plastic', note: 'Switches, stamps & gadgets', src: LASER_VIDEOS.plastic },
  { name: 'Stone', note: 'Slate & 3D relief embossing', src: LASER_VIDEOS.stone },
]

/** 規格卡（替代原 Before/After 指標卡） */
const SPECS = [
  { label: 'Engraving Precision', value: '±0.01 mm' },
  { label: 'Auto Focus', value: '10 s' },
  { label: 'Fastest Logo', value: '3 s' },
  { label: 'Materials', value: '7+ types' },
]

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

/* ── 横向无限瀑布流：跨整行、可向右无限滚动 ─────────────── */
const Rail = styled.div`
  grid-column: 1 / -1;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 1rem;
  flex-wrap: nowrap;
  padding: 4px 4px 24px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
  scrollbar-width: none;
  -ms-overflow-style: none;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }

  &::-webkit-scrollbar {
    display: none;
  }

  & > * {
    scroll-snap-align: start;
  }
`

/** Rail 内的 Reveal：禁止被 flex 压缩，保证卡片保持原尺寸、顶部对齐 */
const RailReveal = styled(Reveal)`
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
`

/* ── 材料卡：影片 + 名称图注 ─────────────────────────────── */
const MaterialCard = styled.figure`
  margin: 0;
  display: flex;
  flex-direction: column;
  width: 240px;
  flex-shrink: 0;
  ${cardSurface};
  border-radius: ${Radius.xl}px;
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.3s cubic-bezier(0.22, 1, 0.36, 1);

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 8px rgba(14, 16, 19, 0.06), 0 16px 40px rgba(14, 16, 19, 0.08);
  }
`

const MaterialVideo = styled(LaserVideo)`
  border-radius: 0;
`

const MaterialCaption = styled.figcaption`
  padding: 0.85rem 1rem;
  border-top: 1px solid ${Ink.rule};
`

const MaterialName = styled.div`
  font-family: ${Font.display};
  font-size: 0.95rem;
  font-weight: 700;
  ${Type.tight}
  color: ${Ink.black};
`

const MaterialNote = styled.div`
  margin-top: 0.2rem;
  font-size: 0.74rem;
  line-height: 1.45;
  color: ${Ink.graphite};
`

/* ── 規格卡（最右侧，竖排） ─────────────────────────────── */
const Specs = styled.div`
  ${cardSurface};
  border-radius: ${Radius.xl}px;
  padding: 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1rem;
  width: 240px;
  height: 380px;
  flex-shrink: 0;
`

const Spec = styled.div`
  text-align: left;
`

const SpecLabel = styled.div`
  ${Type.wideCaps}
  font-size: 0.7rem;
  font-weight: 600;
  color: ${Ink.faint};
  margin-bottom: 0.4rem;
`

const SpecValue = styled.div`
  ${Type.tnum}
  font-family: ${Font.display};
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: ${Ink.black};
`

const SpecNote = styled.div`
  margin-top: 0.2rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: ${Ink.up};
`

export default function Materials() {
  return (
    <Section id="materials">
      <Grid12>
        <HeadRow>
          <Reveal>
            <SectionHead
              eyebrow="Engrave anything"
              tone="brand"
              title="One laser. Seven materials. Zero limits."
              lead="Wood, metal, glass, leather, fabric, plastic, stone — the same machine switches materials in seconds. Every clip below is real CarveNex output."
            />
          </Reveal>
        </HeadRow>

        <Rail data-materials-rail>
          {MATERIALS.map((m, i) => (
            <RailReveal key={m.name} delay={i * 60}>
              <MaterialCard>
                <MaterialVideo src={m.src} ratio="4 / 5" />
                <MaterialCaption>
                  <MaterialName>{m.name}</MaterialName>
                  <MaterialNote>{m.note}</MaterialNote>
                </MaterialCaption>
              </MaterialCard>
            </RailReveal>
          ))}

          <RailReveal delay={480}>
            <Specs data-specs>
              {SPECS.map((s, i) => (
                <Spec key={s.label}>
                  <SpecLabel>{s.label}</SpecLabel>
                  <SpecValue>{s.value}</SpecValue>
                  {i === 0 && <SpecNote>Dia-level accuracy</SpecNote>}
                  {i === 2 && <SpecNote>Done in 10 seconds — really</SpecNote>}
                </Spec>
              ))}
            </Specs>
          </RailReveal>
        </Rail>
      </Grid12>
    </Section>
  )
}
