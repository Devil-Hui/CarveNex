import { useEffect, useRef, useState } from 'react'
import styled, { css, keyframes } from 'styled-components'
import { Font, Ink, Radius, Type, Elevation, cardSurface, gridContainer, Rhythm, Ease, mq } from '../editorial'
import { Reveal } from './Reveal'
import { Button, SectionHead } from './ui/primitives'
import { IconArrowRight } from './ui/Icon'

/**
 * UseCases — AI 定制生成面板（落地页 section[3] 主体）
 * ─────────────────────────────────────────────────────────────
 * 左栏（配置）：
 *   蓝色 chips = 材质（单选） / 紫色 chips = 应用场景（单选）
 *   绿色文本框 = 用户诉求 / 虚线方块 = 上传参考图（上传后原地展示）
 * 右栏（结果）：
 *   点击 Generate 后进入生成态——结果图带高斯模糊蒙版、随进度逐渐清晰；
 *   下方任务清单逐条完成（确定材质场景 → 理解文本 → 分析图片 →
 *   效果图生成 → 三视图生成），全部完成后展示三视图缩略条。
 * 当前为前端效果模拟（先实现效果），尚未接真实生成接口。
 */

/* ── 数据：生成结果为固定静态图（材质实拍首帧，非视频） ────── */
const MATERIALS: { id: string; name: string; poster: string }[] = [
  { id: 'wood', name: 'Wood', poster: '/videos/posters/wood.jpg' },
  { id: 'metal', name: 'Metal', poster: '/videos/posters/metal.jpg' },
  { id: 'glass', name: 'Glass', poster: '/videos/posters/glass.jpg' },
  { id: 'leather', name: 'Leather', poster: '/videos/posters/leather.jpg' },
  { id: 'fabric', name: 'Fabric', poster: '/videos/posters/fabric.jpg' },
  { id: 'plastic', name: 'Plastic', poster: '/videos/posters/plastic.jpg' },
  { id: 'stone', name: 'Stone', poster: '/videos/posters/stone.jpg' },
]

const SCENARIOS = ['3D Embossing', 'Logo', 'Tumblers', 'Gifts', 'Apparel', 'Shoes']

/* ── 生成结果四视图：对应 public/output/ 下的渲染图 ──────────────
 * zheng → 正视 Front ／ fu → 俯视 Top ／ ce → 侧视 Side ／ bei → 背视 Back */
const OUTPUT_VIEWS: { key: string; label: string }[] = [
  { key: 'zheng', label: 'Front' },
  { key: 'fu', label: 'Top' },
  { key: 'ce', label: 'Side' },
  { key: 'bei', label: 'Back' },
]
const OUTPUT_FRONT = `/output/${OUTPUT_VIEWS[0].key}.jpg`

const STEPS = [
  'Confirm material & scenario',
  'Understand your brief',
  'Analyze reference image',
  'Generate product preview',
  'Render three-view drafts',
]

const STEP_MS = 1400
const PURPLE = '#7C3AED'
const PURPLE_SOFT = '#F3EEFF'
const PURPLE_BORDER = '#DDD0FB'

/* ── 區塊 ─────────────────────────────────────────────────── */
const Section = styled.section`
  padding-block: ${Rhythm.section};
  background: ${Ink.paper};
  border-bottom: 1px solid ${Ink.rule};
`

const Grid12 = styled.div`
  ${gridContainer};
  row-gap: clamp(2rem, 5vw, 3rem);
`

const HeadRow = styled.div`
  grid-column: 1 / -1;
`

/* ── 生成面板：左配置 + 右结果 ─────────────────────────────── */
const Panel = styled.div`
  grid-column: 1 / -1;
  ${cardSurface};
  border-radius: ${Radius.xxl}px;
  display: grid;
  grid-template-columns: 1fr;
  overflow: hidden;
  ${mq.mdUp} {
    grid-template-columns: 5fr 6fr;
  }
`

const Config = styled.div`
  padding: clamp(1.25rem, 3vw, 2rem);
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
`

const Field = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
`

const FieldLabel = styled.span<{ $color: string }>`
  ${Type.wideCaps}
  font-size: 11px;
  font-weight: 700;
  color: ${(p) => p.$color};
`

const Chips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
`

const Chip = styled.button<{ $active: boolean; $c: string; $bg: string; $bd: string }>`
  padding: 7px 16px;
  border-radius: ${Radius.full};
  font-family: ${Font.body};
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ${Ease.cinema};
  border: 1px solid ${(p) => (p.$active ? p.$c : p.$bd)};
  background: ${(p) => (p.$active ? p.$c : p.$bg)};
  color: ${(p) => (p.$active ? '#fff' : p.$c)};
  &:hover {
    border-color: ${(p) => p.$c};
    transform: translateY(-1px);
  }
`

const Brief = styled.textarea`
  resize: vertical;
  min-height: 84px;
  padding: 12px 14px;
  border-radius: ${Radius.md}px;
  border: 1.5px solid ${Ink.upBorder};
  background: ${Ink.upSoft};
  font-family: ${Font.body};
  font-size: 14px;
  line-height: 1.6;
  color: ${Ink.black};
  outline: none;
  transition: border-color 0.25s ${Ease.cinema}, box-shadow 0.25s ${Ease.cinema};
  &::placeholder {
    color: ${Ink.faint};
  }
  &:focus {
    border-color: ${Ink.up};
    box-shadow: 0 0 0 3px ${Ink.upSoft};
  }
`

const UploadBox = styled.button<{ $hasImage: boolean }>`
  position: relative;
  width: 100%;
  height: 132px;
  border-radius: ${Radius.lg}px;
  border: 1.5px dashed ${(p) => (p.$hasImage ? 'transparent' : Ink.ruleStrong)};
  background: ${(p) => (p.$hasImage ? 'transparent' : Ink.sunken)};
  cursor: pointer;
  overflow: hidden;
  display: grid;
  place-items: center;
  color: ${Ink.faint};
  font-size: 13px;
  font-weight: 600;
  padding: 0;
  transition: border-color 0.25s ${Ease.cinema};
  &:hover {
    border-color: ${(p) => (p.$hasImage ? 'transparent' : Ink.black)};
  }
  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  span {
    position: relative;
    z-index: 1;
    padding: 4px 12px;
    border-radius: ${Radius.full};
    background: ${(p) => (p.$hasImage ? 'rgba(14,16,19,0.55)' : 'transparent')};
    color: ${(p) => (p.$hasImage ? '#fff' : Ink.faint)};
  }
`

const GenerateButton = styled.button`
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 26px;
  border: none;
  border-radius: ${Radius.full};
  background: ${Ink.brand};
  color: #fff;
  font-family: ${Font.body};
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: ${Elevation.brand};
  transition: all 0.25s ${Ease.cinema};
  &:hover:not(:disabled) {
    background: ${Ink.brandDeep};
    transform: translateY(-2px);
  }
  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    box-shadow: none;
  }
`

/* ── 右侧结果区 ────────────────────────────────────────────── */
const Result = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  border-top: 1px solid ${Ink.rule};
  background: ${Ink.sunken};
  ${mq.mdUp} {
    border-top: none;
    border-left: 1px solid ${Ink.rule};
  }
`

const Stage = styled.div`
  position: relative;
  flex: 1;
  min-height: 300px;
  overflow: hidden;
  display: grid;
  place-items: center;
`

const Placeholder = styled.div`
  color: ${Ink.faint};
  font-size: 14px;
  text-align: center;
  line-height: 1.8;
  padding: 24px;
`

/** 生成中：高斯模糊蒙版随进度逐渐清晰 */
const BlurMedia = styled.div<{ $blur: number }>`
  position: absolute;
  inset: 0;
  filter: blur(${(p) => p.$blur}px);
  transform: scale(1.06); /* 模糊边缘不外溢 */
  transition: filter ${STEP_MS}ms linear;
  video,
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
`

const GeneratingTag = styled.div`
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 2;
  padding: 5px 14px;
  border-radius: ${Radius.full};
  background: rgba(14, 16, 19, 0.62);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  backdrop-filter: blur(4px);
`

/* ── 任务清单：逐条完成 ────────────────────────────────────── */
const spin = keyframes`
  to { transform: rotate(360deg); }
`

const Checklist = styled.ul`
  list-style: none;
  margin: 0;
  padding: 14px clamp(1.25rem, 3vw, 2rem) 18px;
  background: ${Ink.paper};
  border-top: 1px solid ${Ink.rule};
  display: flex;
  flex-direction: column;
  gap: 4px;
`

const StepRow = styled.li<{ $state: 'pending' | 'active' | 'done' }>`
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  padding: 4px 0;
  color: ${(p) => (p.$state === 'pending' ? Ink.faint : Ink.black)};
  font-weight: ${(p) => (p.$state === 'active' ? 700 : 500)};
  transition: color 0.3s ${Ease.cinema};
`

const StepIcon = styled.span<{ $state: 'pending' | 'active' | 'done' }>`
  flex: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  ${(p) =>
    p.$state === 'done' &&
    css`
      background: ${Ink.up};
      color: #fff;
    `}
  ${(p) =>
    p.$state === 'active' &&
    css`
      border: 2px solid ${Ink.brandSoft};
      border-top-color: ${Ink.brand};
      animation: ${spin} 0.8s linear infinite;
    `}
  ${(p) =>
    p.$state === 'pending' &&
    css`
      border: 1.5px solid ${Ink.ruleStrong};
    `}
`

/* ── 三视网格（主图为正视 zheng，下方为俯/侧/背三格） ────────── */
const TriView = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 12px clamp(1.25rem, 3vw, 2rem) 18px;
  background: ${Ink.paper};
  border-top: 1px solid ${Ink.rule};
  animation: tri-in 0.5s ${Ease.cinema};
  @keyframes tri-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
  }
`

const TriCell = styled.div`
  border-radius: ${Radius.md}px;
  overflow: hidden;
  border: 1px solid ${Ink.rule};
  aspect-ratio: 4 / 3;
  position: relative;
  video,
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  span {
    position: absolute;
    left: 6px;
    bottom: 6px;
    padding: 2px 8px;
    border-radius: ${Radius.full};
    background: rgba(14, 16, 19, 0.6);
    color: #fff;
    font-size: 10.5px;
    font-weight: 700;
  }
`

/* ── CTA ──────────────────────────────────────────────────── */
const CtaWrap = styled.div`
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
`

export default function UseCases() {
  const [material, setMaterial] = useState<string | null>(null)
  const [scenario, setScenario] = useState<string | null>(null)
  const [brief, setBrief] = useState('')
  const [image, setImage] = useState<string | null>(null)
  const [phase, setPhase] = useState<'idle' | 'generating' | 'done'>('idle')
  const [step, setStep] = useState(0)
  const fileInput = useRef<HTMLInputElement>(null)

  const ready = material !== null && scenario !== null

  /* 任务清单逐条推进：step 0→5，每条 STEP_MS */
  useEffect(() => {
    if (phase !== 'generating') return
    if (step >= STEPS.length) {
      setPhase('done')
      return
    }
    const t = setTimeout(() => setStep((s) => s + 1), STEP_MS)
    return () => clearTimeout(t)
  }, [phase, step])

  const generate = () => {
    if (!ready) return
    setStep(0)
    setPhase('generating')
  }

  const onUpload = (files: FileList | null) => {
    const f = files?.[0]
    if (!f || !f.type.startsWith('image/')) return
    setImage((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(f)
    })
  }

  /* 高斯模糊蒙版：随任务进度逐渐清晰（22px → 0） */
  const blur =
    phase === 'idle' ? 0 : Math.max(0, 22 - (step / STEPS.length) * 24)

  /* 生成结果为固定四视图渲染图（与上传图无关）：主预览取正视 zheng，三视图区展示全部四张 */
  const media = <img src={OUTPUT_FRONT} alt="Design preview" />

  return (
    <Section id="use-cases">
      <Grid12>
        <HeadRow>
          <Reveal>
            <SectionHead
              eyebrow="Real projects"
              title="What will you make first?"
              lead="Pick a material and a scenario, describe your idea — watch a custom preview come together, step by step."
            />
          </Reveal>
        </HeadRow>

        <Panel>
          {/* 左栏：配置 */}
          <Config>
            <Field>
              <FieldLabel $color={Ink.blue}>Material</FieldLabel>
              <Chips>
                {MATERIALS.map((m) => (
                  <Chip
                    key={m.id}
                    type="button"
                    $active={material === m.id}
                    $c={Ink.blue}
                    $bg={Ink.blueSoft}
                    $bd={Ink.blueBorder}
                    onClick={() => setMaterial(m.id)}
                  >
                    {m.name}
                  </Chip>
                ))}
              </Chips>
            </Field>

            <Field>
              <FieldLabel $color={PURPLE}>Application</FieldLabel>
              <Chips>
                {SCENARIOS.map((s) => (
                  <Chip
                    key={s}
                    type="button"
                    $active={scenario === s}
                    $c={PURPLE}
                    $bg={PURPLE_SOFT}
                    $bd={PURPLE_BORDER}
                    onClick={() => setScenario(s)}
                  >
                    {s}
                  </Chip>
                ))}
              </Chips>
            </Field>

            <Field>
              <FieldLabel $color={Ink.up}>Your idea</FieldLabel>
              <Brief
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="Names, dates, a quote, a logo style…"
                maxLength={200}
              />
            </Field>

            <Field>
              <FieldLabel $color={Ink.graphite}>Reference image</FieldLabel>
              <UploadBox
                type="button"
                $hasImage={!!image}
                onClick={() => fileInput.current?.click()}
              >
                {image && <img src={image} alt="Reference" />}
                <span>{image ? 'Click to replace' : '＋ Upload image'}</span>
              </UploadBox>
              <input
                ref={fileInput}
                type="file"
                accept="image/*"
                hidden
                onChange={(e) => {
                  onUpload(e.target.files)
                  e.target.value = ''
                }}
              />
            </Field>

            <GenerateButton type="button" disabled={!ready || phase === 'generating'} onClick={generate}>
              {phase === 'generating' ? 'Generating…' : 'Generate Preview'}
            </GenerateButton>
          </Config>

          {/* 右栏：生成结果 */}
          <Result>
            <Stage>
              {phase === 'idle' ? (
                <Placeholder>
                  Your design preview
                  <br />
                  will appear here
                </Placeholder>
              ) : (
                <>
                  {phase === 'generating' && <GeneratingTag>Generating…</GeneratingTag>}
                  <BlurMedia $blur={blur}>{media}</BlurMedia>
                </>
              )}
            </Stage>

            {phase !== 'idle' && (
              <Checklist>
                {STEPS.map((label, i) => {
                  const state = i < step || phase === 'done' ? 'done' : i === step ? 'active' : 'pending'
                  return (
                    <StepRow key={label} $state={state}>
                      <StepIcon $state={state}>{state === 'done' ? '✓' : ''}</StepIcon>
                      {label}
                    </StepRow>
                  )
                })}
              </Checklist>
            )}

            {phase === 'done' && (
              <TriView>
                {OUTPUT_VIEWS.filter((v) => v.key !== 'zheng').map(({ key, label }) => (
                  <TriCell key={key}>
                    <img src={`/output/${key}.jpg`} alt={`${label} view`} />
                    <span>{label}</span>
                  </TriCell>
                ))}
              </TriView>
            )}
          </Result>
        </Panel>

        <CtaWrap>
          <Reveal delay={120}>
            <Button href="#start">
              Start Your First Project <IconArrowRight />
            </Button>
          </Reveal>
        </CtaWrap>
      </Grid12>
    </Section>
  )
}
