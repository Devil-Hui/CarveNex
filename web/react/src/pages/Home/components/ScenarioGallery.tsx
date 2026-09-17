import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import { Ink, Font, Display, Radius, Elevation, Ease, Rhythm, gridContainer, mq } from '../editorial'
import { SCENARIO_ROWS, type ScenarioRow, type ScenarioVideo } from '../data/scenarioGallery'

/**
 * 应用场景视频画廊（首页 section[2]）
 * ─────────────────────────────────────────────────────────────
 * 三态状态机：
 *   ① 滚动态  上下两行无限横向滚动（上行左滚 / 下行右滚），卡片为视频首帧
 *   ② 聚焦态  点击卡片 → 放大居中（z 轴最高层），其余区域遮罩微模糊；
 *             卡片上下 8:2，下部含「返回」「展开」两按钮，点上部播放视频
 *   ③ 展开态  本行全部卡片按分类从左上逐行均匀网格排布，每个分类
 *             一行文字说明（可开关）；右上角「文字说明」与「返回」按钮
 * 右上角「添加视频」支持批量选择：读取本地文件时显示真实字节进度条，
 * 逐个追加到首行「Uploads」分类（会话内 blob 预览），并给新增卡片加「NEW」角标；
 * 追加后跑马灯立即滚动到新卡片，点开它进入展开态即可在视频墙看到。
 */

/* ── 数据 ─────────────────────────────────────────────────── */
interface GalleryItem {
  key: string
  /** 所属行类型（Materials / Applications） */
  rowName: string
  catName: string
  video: ScenarioVideo
}

const flattenRow = (row: ScenarioRow): GalleryItem[] =>
  row.categories.flatMap((c) =>
    c.videos.map((v) => ({
      key: `${row.id}/${c.id}/${v.id}`,
      rowName: row.name,
      catName: c.name,
      video: v,
    })),
  )

/**
 * 读取本地文件字节以驱动真实进度条：只统计已读字节、不保留内容，
 * 因此大文件也不会把整个视频放进内存；读完后仍用 URL.createObjectURL(file)。
 */
function readWithProgress(file: File, onProgress: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const reader = file.stream().getReader()
    let read = 0
    const pump = (): void => {
      reader.read().then(({ done, value }) => {
        if (done) {
          onProgress(1)
          resolve()
          return
        }
        read += value?.length ?? 0
        onProgress(file.size ? Math.min(read / file.size, 1) : 1)
        pump()
      }, reject)
    }
    pump()
  })
}

/**
 * 默认自动播放的本地视频（静音循环）。
 * IntersectionObserver 控制：进入视口才 play（触发加载并播放）、离开即 pause。
 * preload="none" + 按需 play 避免双行 marquee 上百个 <video> 同时抢占
 * HTTP/1.1 连接（同源 6 并发上限）导致的加载风暴与黑帧。
 */
function AutoVideo({ src, className }: { src: string; className?: string }) {
  const ref = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) el.play().catch(() => {})
        else el.pause()
      },
      { rootMargin: '160px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [src])
  return (
    <video
      ref={ref}
      className={className}
      src={src}
      muted
      loop
      playsInline
      preload="none"
      aria-hidden="true"
    />
  )
}

/* ── 区块 ─────────────────────────────────────────────────── */
const Section = styled.section`
  position: relative;
  padding-block: ${Rhythm.section};
  background: ${Ink.paperAlt};
  overflow: hidden;
`

const Head = styled.div`
  ${gridContainer}
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: clamp(1.5rem, 3vw, 2.5rem);
`

const Eyebrow = styled.p`
  font-family: ${Font.body};
  font-size: 12px;
  letter-spacing: 0.14em;
  font-weight: 600;
  color: ${Ink.brand};
  margin: 0 0 8px;
`

const Title = styled.h2`
  font-family: ${Font.display};
  font-size: ${Display.giant};
  line-height: 1.15;
  margin: 0;
`

const Sub = styled.p`
  color: ${Ink.graphite};
  font-size: 0.95rem;
  margin: 8px 0 0;
`

const AddButton = styled.button`
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  border-radius: ${Radius.full};
  background: ${Ink.black};
  color: ${Ink.paper};
  font-family: ${Font.body};
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: ${Elevation.ink};
  transition: transform 0.3s ${Ease.cinema}, background 0.3s ${Ease.cinema};
  &:hover {
    background: ${Ink.brand};
    transform: translateY(-2px);
  }
`

/* ── 双行无限滚动（Magic UI Marquee 同原理：两组内容平移 -50%） ── */
const marquee = keyframes`
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(-50%, 0, 0); }
`

const MarqueeRow = styled.div`
  overflow: hidden;
  padding-block: 10px;
  mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent);
  &:hover [data-track] {
    animation-play-state: paused;
  }
`

/** 每一行跑马灯的行标题（上行 Materials / 下行 Use Cases）：与区块同字体、黑色、无上下间距 */
const RowLabel = styled.p`
  ${gridContainer}
  margin-block: 0;
  font-family: ${Font.body};
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: ${Ink.black};
`

const Track = styled.div<{ $dur: number; $reverse?: boolean }>`
  display: flex;
  gap: 16px;
  width: max-content;
  animation: ${marquee} ${(p) => p.$dur}s linear infinite;
  animation-direction: ${(p) => (p.$reverse ? 'reverse' : 'normal')};
`

const Card = styled.button<{ $isNew?: boolean }>`
  position: relative;
  flex: none;
  width: clamp(140px, 16vw, 200px);
  aspect-ratio: 3 / 4;
  padding: 0;
  border: 1px solid ${(p) => (p.$isNew ? Ink.brand : Ink.rule)};
  border-radius: ${Radius.lg}px;
  overflow: hidden;
  background: ${Ink.sunken};
  cursor: pointer;
  box-shadow: ${Elevation.card};
  transition: transform 0.3s ${Ease.cinema}, box-shadow 0.3s ${Ease.cinema};
  &:hover {
    transform: translateY(-4px);
    box-shadow: ${Elevation.hover};
  }
  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    pointer-events: none;
  }
`

const CardChip = styled.span`
  position: absolute;
  left: 8px;
  bottom: 8px;
  max-width: calc(100% - 16px);
  padding: 3px 10px;
  border-radius: ${Radius.full};
  background: rgba(14, 16, 19, 0.62);
  color: #fff;
  font-size: 12px;
  line-height: 1.6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  backdrop-filter: blur(4px);
`

/** 新增项角标：与既有实拍视频做轻微区分 */
const NewBadge = styled.span`
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  padding: 2px 8px;
  border-radius: ${Radius.full}px;
  background: ${Ink.brand};
  color: #fff;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.04em;
  box-shadow: ${Elevation.brand};
`

/* ── 遮罩（点击空白 = 返回） ───────────────────────────────── */
const Scrim = styled.div`
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(14, 16, 19, 0.42);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
`

/* ── 聚焦态：放大卡片（上下 8:2） ──────────────────────────── */
const ZoomLayer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  pointer-events: none;
`

const ZoomCard = styled.div`
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  width: min(400px, 86vw);
  height: min(560px, 78vh);
  border-radius: ${Radius.xl}px;
  overflow: hidden;
  background: ${Ink.paper};
  box-shadow: ${Elevation.float};
  animation: zoom-in 0.35s ${Ease.cinema};
  @keyframes zoom-in {
    from { transform: scale(0.82); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }
`

const ZoomUpper = styled.button`
  flex: 8 1 0;
  min-height: 0;
  padding: 0;
  border: none;
  background: ${Ink.near};
  cursor: pointer;
  position: relative;
  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    pointer-events: none;
  }
  &::after {
    content: '▶ Play';
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    color: #fff;
    font-size: 15px;
    font-weight: 600;
    background: rgba(14, 16, 19, 0.28);
    opacity: 0;
    transition: opacity 0.25s ${Ease.cinema};
  }
  &:hover::after {
    opacity: 1;
  }
`

const ZoomLower = styled.div`
  flex: 0 0 20%;
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 18px;
  border-top: 1px solid ${Ink.rule};
`

const ZoomName = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: ${Ink.black};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

/** 「类型 | 名字」中间的竖线：左右各留一点间距即可 */
const ZoomSep = styled.span`
  padding-inline: 5px;
  color: ${Ink.faint};
  font-weight: 400;
`

const GhostButton = styled.button`
  padding: 8px 16px;
  border: 1px solid ${Ink.ruleStrong};
  border-radius: ${Radius.full};
  background: ${Ink.paper};
  color: ${Ink.black};
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ${Ease.cinema};
  &:hover {
    border-color: ${Ink.black};
  }
`

const SolidButton = styled(GhostButton)`
  border: none;
  background: ${Ink.brand};
  color: #fff;
  box-shadow: ${Elevation.brand};
  &:hover {
    background: ${Ink.brandDeep};
  }
`

/* ── 展开态：分类网格列表 ──────────────────────────────────── */
const ExpandLayer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 80;
  background: ${Ink.paper};
  overflow-y: auto;
  animation: expand-in 0.3s ${Ease.cinema};
  @keyframes expand-in {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: none; }
  }
`

const ExpandBar = styled.div`
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px clamp(1.25rem, 4vw, 3rem);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid ${Ink.rule};
  h3 {
    margin: 0;
    font-family: ${Font.display};
    font-size: 1.25rem;
  }
`

const ExpandActions = styled.div`
  display: flex;
  gap: 10px;
`

const ExpandBody = styled.div`
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px clamp(1.25rem, 4vw, 3rem) 64px;
`

const CatBlock = styled.div`
  & + & {
    margin-top: 40px;
  }
`

const CatNote = styled.p`
  margin: 0 0 10px;
  font-size: 15px;
  color: ${Ink.graphite};
  strong {
    color: ${Ink.black};
    margin-right: 8px;
  }
`

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;
  ${mq.mdDown} {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }
`

const GridCard = styled(Card)`
  width: 100%;
`

const GridLabel = styled.div`
  margin-top: 6px;
  font-size: 12px;
  color: ${Ink.faint};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

/* ── 播放层（第二/三态点击卡片后播放原视频） ────────────────── */
const PlayerLayer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  background: rgba(14, 16, 19, 0.86);
  backdrop-filter: blur(8px);
`

const PlayerBox = styled.div`
  width: min(880px, 92vw);
  video {
    width: 100%;
    max-height: 80vh;
    border-radius: ${Radius.lg}px;
    background: #000;
    display: block;
  }
`

const PlayerClose = styled.button`
  position: fixed;
  top: 20px;
  right: 24px;
  z-index: 91;
  padding: 8px 18px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: ${Radius.full};
  background: transparent;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  &:hover {
    background: rgba(255, 255, 255, 0.14);
  }
`

/* ── 添加进度（等待反馈） ─────────────────────────────────── */
const ProgressToast = styled.div`
  position: fixed;
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  z-index: 95;
  min-width: 264px;
  padding: 12px 16px;
  border-radius: ${Radius.lg}px;
  background: rgba(14, 16, 19, 0.9);
  color: #fff;
  box-shadow: ${Elevation.float};
  backdrop-filter: blur(6px);
`

const ProgressLabel = styled.div`
  display: flex;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
  font-size: 12.5px;
  font-weight: 600;
`

const ProgressTrack = styled.div`
  height: 5px;
  border-radius: ${Radius.full}px;
  background: rgba(255, 255, 255, 0.22);
  overflow: hidden;
`

const ProgressFill = styled.div<{ $pct: number }>`
  height: 100%;
  width: ${(p) => Math.round(p.$pct * 100)}%;
  background: ${Ink.brand};
  transition: width 0.18s ${Ease.cinema};
`

/* ── 组件 ─────────────────────────────────────────────────── */
export default function ScenarioGallery() {
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploads, setUploads] = useState<ScenarioVideo[]>([])
  /** 本次会话新增的视频 id：用于跑马灯/视频墙上的「NEW」区分 */
  const [newIds, setNewIds] = useState<Set<string>>(() => new Set())
  /** 添加进度：读取本地文件时的等待反馈 */
  const [adding, setAdding] = useState<{ done: number; total: number; pct: number } | null>(null)
  const [focus, setFocus] = useState<{ rowId: string; item: GalleryItem } | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [playing, setPlaying] = useState<ScenarioVideo | null>(null)
  const [showNotes, setShowNotes] = useState(true)

  /** 上传的视频并入首行「新上传」分类 */
  const rows = useMemo<ScenarioRow[]>(() => {
    if (!uploads.length) return SCENARIO_ROWS
    const [first, ...rest] = SCENARIO_ROWS
    const cat = { id: 'uploads', name: 'Uploads', desc: 'Fresh local uploads', videos: uploads }
    return [{ ...first, categories: [cat, ...first.categories.filter((c) => c.id !== 'uploads')] }, ...rest]
  }, [uploads])

  const expandRow = useMemo(
    () => (focus ? rows.find((r) => r.id === focus.rowId) ?? null : null),
    [focus, rows],
  )

  /**
   * 批量添加视频：逐个「读取（真实字节进度）→ 生成预览 → 立即追加」。
   * 追加进首行「Uploads」分类后：跑马灯立刻滚动到它；点开卡片进入展开态即出现在视频墙。
   */
  const onUpload = async (files: File[] | null) => {
    const list = (files ?? []).filter(
      (f) => f.type.startsWith('video/') || /\.(mp4|mov|webm|m4v)$/i.test(f.name),
    )
    if (!list.length) return
    setAdding({ done: 0, total: list.length, pct: 0 })
    for (let i = 0; i < list.length; i++) {
      const file = list[i]
      const started = Date.now()
      await readWithProgress(file, (pct) => setAdding({ done: i, total: list.length, pct }))
      // 小文件读取极快，保留最短可见时长，让进度条能被看见
      const wait = 420 - (Date.now() - started)
      if (wait > 0) await new Promise((r) => setTimeout(r, wait))
      const video: ScenarioVideo = {
        id: `up-${Date.now()}-${i}`,
        title: file.name.replace(/\.[^.]+$/, ''),
        url: URL.createObjectURL(file),
      }
      setUploads((prev) => [...prev, video])
      setNewIds((prev) => new Set(prev).add(video.id))
      setAdding({ done: i + 1, total: list.length, pct: 1 })
    }
    setAdding(null)
  }

  const closeFocus = useCallback(() => {
    setFocus(null)
    setExpanded(false)
  }, [])

  /* Esc 逐级返回：播放层 → 展开态 → 聚焦态 → 滚动态 */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (playing) setPlaying(null)
      else if (expanded) setExpanded(false)
      else if (focus) closeFocus()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [playing, expanded, focus, closeFocus])

  /* 浮层打开时锁定页面滚动 */
  useEffect(() => {
    document.body.style.overflow = focus ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [focus])

  return (
    <Section aria-label="Real-World Scenarios">
      <Head>
        <div>
          <Eyebrow>SCENARIOS</Eyebrow>
          <Title>Real-World Scenarios</Title>
          <Sub>Tap any card to play</Sub>
        </div>
        <AddButton type="button" onClick={() => fileInput.current?.click()}>
          + Add Videos
        </AddButton>
        <input
          ref={fileInput}
          type="file"
          accept="video/*"
          multiple
          hidden
          onChange={(e) => {
            const picked = e.target.files ? Array.from(e.target.files) : null
            e.target.value = ''
            void onUpload(picked)
          }}
        />
      </Head>

      {rows.map((row, rowIdx) => {
        const items = flattenRow(row)
        const doubled = [...items, ...items]
        return (
          <Fragment key={row.id}>
            <RowLabel>{row.name}</RowLabel>
            <MarqueeRow aria-label={row.name}>
              <Track data-track $dur={Math.max(items.length * 5, 24)} $reverse={rowIdx % 2 === 1}>
                {doubled.map((item, i) => (
                  <Card
                    key={`${item.key}-${i}`}
                    type="button"
                    aria-hidden={i >= items.length}
                    tabIndex={i >= items.length ? -1 : 0}
                    title={item.video.title}
                    $isNew={newIds.has(item.video.id)}
                    onClick={() => setFocus({ rowId: row.id, item })}
                  >
                    <AutoVideo src={item.video.url} />
                    {newIds.has(item.video.id) && <NewBadge>NEW</NewBadge>}
                    <CardChip>{item.catName}</CardChip>
                  </Card>
                ))}
              </Track>
            </MarqueeRow>
          </Fragment>
        )
      })}

      {/* ② 聚焦态 */}
      {focus && (
        <>
          <Scrim onClick={closeFocus} />
          <ZoomLayer>
            <ZoomCard role="dialog" aria-label={focus.item.video.title}>
              <ZoomUpper type="button" onClick={() => setPlaying(focus.item.video)}>
                <AutoVideo src={focus.item.video.url} />
              </ZoomUpper>
              <ZoomLower>
                <ZoomName>
                  {focus.item.rowName}
                  <ZoomSep aria-hidden="true">|</ZoomSep>
                  {focus.item.catName}
                </ZoomName>
                <div style={{ display: 'flex', gap: 10, flex: 'none' }}>
                  <GhostButton type="button" onClick={closeFocus}>
                    Back
                  </GhostButton>
                  <SolidButton type="button" onClick={() => setExpanded(true)}>
                    Expand
                  </SolidButton>
                </div>
              </ZoomLower>
            </ZoomCard>
          </ZoomLayer>
        </>
      )}

      {/* ③ 展开态：本行卡片按分类网格排布 */}
      {focus && expanded && expandRow && (
        <ExpandLayer role="dialog" aria-label={`${expandRow.name} list`}>
          <ExpandBar>
            <h3>{expandRow.name}</h3>
            <ExpandActions>
              <GhostButton
                type="button"
                role="switch"
                aria-checked={showNotes}
                onClick={() => setShowNotes((v) => !v)}
              >
                Captions: {showNotes ? 'On' : 'Off'}
              </GhostButton>
              <SolidButton type="button" onClick={() => setExpanded(false)}>
                Back
              </SolidButton>
            </ExpandActions>
          </ExpandBar>
          <ExpandBody>
            {expandRow.categories.map((cat) => (
              <CatBlock key={cat.id}>
                {showNotes && (
                  <CatNote>
                    <strong>{cat.name}</strong>
                    {cat.desc}
                  </CatNote>
                )}
                <Grid>
                  {cat.videos.map((v) => (
                    <div key={v.id}>
                      <GridCard
                        type="button"
                        title={v.title}
                        $isNew={newIds.has(v.id)}
                        onClick={() => setPlaying(v)}
                      >
                        <AutoVideo src={v.url} />
                        {newIds.has(v.id) && <NewBadge>NEW</NewBadge>}
                      </GridCard>
                      <GridLabel>{v.title}</GridLabel>
                    </div>
                  ))}
                </Grid>
              </CatBlock>
            ))}
          </ExpandBody>
        </ExpandLayer>
      )}

      {/* 播放层：第二/三态点击卡片播放原视频 */}
      {playing && (
        <PlayerLayer onClick={() => setPlaying(null)}>
          <PlayerClose type="button" onClick={() => setPlaying(null)}>
            Close
          </PlayerClose>
          <PlayerBox onClick={(e) => e.stopPropagation()}>
            <video src={playing.url} controls autoPlay playsInline />
          </PlayerBox>
        </PlayerLayer>
      )}

      {/* 添加进度：读取本地文件时的等待反馈 */}
      {adding && (
        <ProgressToast role="status" aria-live="polite">
          <ProgressLabel>
            <span>正在添加视频 {Math.min(adding.done + 1, adding.total)}/{adding.total}</span>
            <span>{Math.round(adding.pct * 100)}%</span>
          </ProgressLabel>
          <ProgressTrack>
            <ProgressFill $pct={adding.pct} />
          </ProgressTrack>
        </ProgressToast>
      )}
    </Section>
  )
}
