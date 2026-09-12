import styled, { keyframes } from 'styled-components'
import { Ink, Font, Display, Type, Radius, Elevation, gridContainer, Ease, mq } from '../editorial'
import { MaskLine, Reveal } from './Reveal'
import LaserVideo, { LASER_VIDEOS } from './ui/LaserVideo'
import { IconSparkles, IconStar, IconPlay, IconArrowRight, IconUsers } from './ui/Icon'

const fadeUp = keyframes`
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
`

/**
 * Hero — 左標題 + 右實拍雕刻影片構圖
 * 產品價值前置：以真實激光雕刻畫面建立「所見即所得」的信任。
 */
const Section = styled.section`
  position: relative;
  overflow: hidden;
  padding: clamp(6.5rem, 12vh, 9rem) 0 clamp(2.5rem, 5vw, 4rem);
  background: ${Ink.paper};
  border-bottom: 1px solid ${Ink.rule};
`

/** 背景柔光：品牌紅極淡暈染，僅作層次，不搶內容 */
const Blob = styled.span`
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: 0;
`

const BlobA = styled(Blob)`
  width: 460px;
  height: 460px;
  background: rgba(254, 44, 85, 0.07);
  top: -140px;
  right: -80px;
`

const BlobB = styled(Blob)`
  width: 380px;
  height: 380px;
  background: rgba(35, 88, 216, 0.06);
  bottom: -120px;
  left: -120px;
`

const Grid12 = styled.div`
  ${gridContainer};
  position: relative;
  z-index: 1;
  align-items: center;
  row-gap: clamp(2.5rem, 6vw, 4rem);
`

/* ── 左欄 ───────────────────────────────────────────────── */
const Left = styled.div`
  grid-column: 1 / -1;
  ${mq.mdUp} {
    grid-column: 1 / 7;
  }
`

const Badge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.85rem;
  border-radius: ${Radius.full}px;
  background: ${Ink.brandSoft};
  border: 1px solid ${Ink.brandBorder};
  color: ${Ink.brand};
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  margin-bottom: 1.4rem;
  animation: ${fadeUp} 0.8s ${Ease.cinema} both;

  svg {
    width: 14px;
    height: 14px;
  }
`

const Title = styled.h1`
  font-family: ${Font.display};
  font-size: ${Display.hero};
  font-weight: 800;
  line-height: 1.03;
  ${Type.tighter}
  color: ${Ink.black};
  margin: 0 0 1.1rem;

  em {
    font-style: normal;
    color: ${Ink.brand};
  }
`

const Sub = styled.p`
  font-size: clamp(0.95rem, 1.2vw, 1.075rem);
  line-height: 1.65;
  color: ${Ink.graphite};
  max-width: 46ch;
  margin: 0 0 1.9rem;
  animation: ${fadeUp} 0.8s ${Ease.cinema} 0.5s both;
`

const CtaRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 2.1rem;
  animation: ${fadeUp} 0.8s ${Ease.cinema} 0.6s both;
`

const PrimaryCta = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.9rem 1.65rem;
  border-radius: ${Radius.full}px;
  background: ${Ink.black};
  color: ${Ink.paper};
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  box-shadow: ${Elevation.ink};
  transition: background 0.3s ${Ease.cinema}, transform 0.3s ${Ease.cinema};

  &:hover {
    background: #000;
    transform: translateY(-2px);
  }

  svg {
    width: 16px;
    height: 16px;
  }
`

const GhostCta = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.9rem 1.65rem;
  border-radius: ${Radius.full}px;
  background: ${Ink.paper};
  border: 1px solid ${Ink.ruleStrong};
  color: ${Ink.black};
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  transition: border-color 0.3s ease, color 0.3s ease, transform 0.3s ease;

  &:hover {
    border-color: ${Ink.black};
    transform: translateY(-2px);
  }

  svg {
    width: 16px;
    height: 16px;
  }
`

/* ── 社交證明 ───────────────────────────────────────────── */
const Proof = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  animation: ${fadeUp} 0.8s ${Ease.cinema} 0.7s both;
`

const Avatars = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 82px;
  height: 34px;
  border-radius: ${Radius.full}px;
  background: ${Ink.sunken};
  border: 1px solid ${Ink.rule};
  color: ${Ink.graphite};

  svg {
    width: 20px;
    height: 20px;
  }
`

const ProofText = styled.div`
  font-size: 0.82rem;
  color: ${Ink.graphite};
  line-height: 1.45;

  strong {
    display: block;
    color: ${Ink.black};
    font-weight: 700;
    font-size: 0.88rem;
  }
`

const Stars = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 1px;
  color: ${Ink.amber};
  vertical-align: -1px;

  svg {
    width: 13px;
    height: 13px;
  }
`

/* ── 右欄：實拍雕刻影片 + 場景標籤 ─────────────────────── */
const Right = styled.div`
  grid-column: 1 / -1;
  position: relative;
  ${mq.mdUp} {
    grid-column: 7 / 13;
  }
`

const Stage = styled.div`
  position: relative;
  max-width: 340px;
  margin-inline: auto;
`

/** 展示框：大圓角影片卡 + 底部狀態列，替代原 TikTok 手機殼 */
const Showcase = styled.figure`
  margin: 0;
  border-radius: ${Radius.xxl}px;
  overflow: hidden;
  border: 1px solid ${Ink.rule};
  background: ${Ink.near};
  box-shadow: ${Elevation.float};
  animation: ${fadeUp} 1s ${Ease.cinema} 0.2s both;
`

const Statusbar = styled.figcaption`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 1.1rem;
  background: ${Ink.paper2};
  border-top: 1px solid ${Ink.rule};
`

const StatusLabel = styled.span`
  ${Type.wideCaps}
  font-size: 10.5px;
  font-weight: 700;
  color: ${Ink.faint};
`

const StatusLive = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: ${Ink.brand};

  &::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: ${Ink.brand};
    animation: pulse 1.6s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.35;
    }
  }
`

export default function Hero() {
  return (
    <Section id="top">
      <BlobA />
      <BlobB />
      <Grid12>
        <Left>
          <Badge>
            <IconSparkles /> Portable Laser Engraver
          </Badge>
          <Title>
            <MaskLine delay={80}>From Idea to</MaskLine>
            <MaskLine delay={160}>
              <em>Engraved</em> Object,
            </MaskLine>
            <MaskLine delay={240}>On Almost Any</MaskLine>
            <MaskLine delay={320}>Material You Love</MaskLine>
          </Title>
          <Sub>
            CarveNex turns sketches, photos and logos into real, touchable pieces — wood, metal,
            glass, leather and more. Design on your phone, autofocus in seconds, engrave in
            minutes. No workshop required.
          </Sub>
          <CtaRow>
            <PrimaryCta href="#start">
              Shop the Engraver <IconArrowRight />
            </PrimaryCta>
            <GhostCta href="#materials">
              <IconPlay /> See What It Can Engrave
            </GhostCta>
          </CtaRow>
          <Proof>
            <Avatars>
              <IconUsers />
            </Avatars>
            <ProofText>
              <strong>
                <Stars>
                  <IconStar />
                  <IconStar />
                  <IconStar />
                  <IconStar />
                  <IconStar />
                </Stars>{' '}
                4.9 · 12,000+ makers
              </strong>
              Community across 60+ countries
            </ProofText>
          </Proof>
        </Left>

        <Right>
          <Reveal delay={100}>
            <Stage>
              <Showcase>
                <LaserVideo src={LASER_VIDEOS.hero} ratio="4 / 5" />
                <Statusbar>
                  <StatusLabel>Now engraving · Multi-material reel</StatusLabel>
                  <StatusLive>LIVE</StatusLive>
                </Statusbar>
              </Showcase>
            </Stage>
          </Reveal>
        </Right>
      </Grid12>
    </Section>
  )
}
