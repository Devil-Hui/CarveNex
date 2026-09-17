/**
 * 推广精投 · 管理端（真实投放操作页）
 *
 * 表格：行 = 在售商品（与商品管理实时同步，名称只读），列 = 海外投放平台。
 * 单元格点击进入编辑态，Enter/失焦确认、Esc 取消；修改未保存的值红色高亮，
 * 左下角灰色划线小字显示上一版金额；点历史图标查看版本链。
 * 保存携带 base_version 乐观锁，冲突（他人先保存）时提示并刷新。
 * 有待保存改动时，底部浮出毛玻璃保存条（改动数 / 保存 / 撤销）。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import { useTranslation } from '../../i18n'
import { localizedText } from '../../utils/localizedText'
import { Color, Radius, Shadow, Spacing, FontSize, FontWeight, Type, Transition } from '../../theme/tokens'
import { Empty, Modal, Pagination, Skeleton, toast } from '../../components/admin/common'
import { Icon } from '../../components/admin/common/Icon'
import SmartImage from '../../components/common/SmartImage/SmartImage'
import { optionalMediaUrl } from '../../utils/mediaUrl'
import {
  adsAPI,
  type AdPlatform,
  type CampaignHistoryItem,
  type CampaignRow,
  type CampaignSaveItem,
} from '../../api/ads'

/* ───────────────────────── 样式 ───────────────────────── */

const Wrap = styled.div`
  padding: ${Spacing.xl}px ${Spacing.xxl}px ${Spacing.xxxl}px;
`

const Head = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: ${Spacing.lg}px;
  flex-wrap: wrap;
`

const TitleWrap = styled.div`
  display: flex;
  align-items: center;
  gap: 14px;
`

const TitleBadge = styled.div`
  width: 44px;
  height: 44px;
  border-radius: ${Radius.lg}px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, ${Color.brand}, #ff6b4a);
  box-shadow: 0 6px 16px ${Color.brand}40;

  svg {
    width: 22px;
    height: 22px;
  }
`

const Title = styled.h1`
  margin: 0;
  font-size: ${FontSize.xxl}px;
  font-weight: ${FontWeight.bold};
  color: ${Color.text.heading};
  ${Type.tight}
`

const Sub = styled.p`
  margin: 3px 0 0;
  color: ${Color.text.muted};
  font-size: ${FontSize.sm}px;
`

const StatChips = styled.div`
  display: flex;
  gap: ${Spacing.sm}px;
  margin-top: 10px;
  flex-wrap: wrap;
`

const StatChip = styled.span<{ $accent?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: ${Radius.full}px;
  font-size: ${FontSize.xs}px;
  font-weight: ${FontWeight.medium};
  ${Type.tnum}
  color: ${({ $accent }) => ($accent ? '#fff' : Color.text.secondary)};
  background: ${({ $accent }) => ($accent ? Color.brand : Color.bg.card)};
  border: 1px solid ${({ $accent }) => ($accent ? 'transparent' : Color.border.light)};

  b {
    font-weight: ${FontWeight.bold};
  }
`

const Actions = styled.div`
  display: flex;
  gap: ${Spacing.sm}px;
  align-items: center;
`

const Btn = styled.button<{ $primary?: boolean }>`
  height: 36px;
  padding: 0 16px;
  border-radius: ${Radius.input}px;
  border: 1px solid ${({ $primary }) => ($primary ? 'transparent' : Color.border.medium)};
  background: ${({ $primary }) => ($primary ? Color.primary : Color.bg.card)};
  color: ${({ $primary }) => ($primary ? Color.text.inverse : Color.text.body)};
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.medium};
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: opacity ${Transition.fast}, box-shadow ${Transition.fast};

  &:hover:not(:disabled) { opacity: 0.88; }
  &:disabled { opacity: 0.45; cursor: not-allowed; }
`

const DirtyChip = styled.span`
  ${Type.tnum}
  background: ${Color.brand};
  color: #fff;
  border-radius: ${Radius.full}px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-size: 11px;
  font-weight: ${FontWeight.bold};
  display: inline-flex;
  align-items: center;
  justify-content: center;
`

const TableCard = styled.div`
  background: ${Color.bg.card};
  border: 1px solid ${Color.border.light};
  border-radius: ${Radius.panel}px;
  box-shadow: ${Shadow.card};
  overflow: auto;
`

const Table = styled.table`
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 860px;

  th, td {
    border-bottom: 1px solid ${Color.border.light};
    padding: 10px 12px;
    text-align: left;
    vertical-align: middle;
  }

  thead th {
    background: ${Color.bg.sunken};
    font-size: ${FontSize.xs}px;
    font-weight: ${FontWeight.semibold};
    color: ${Color.text.muted};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    position: sticky;
    top: 0;
    z-index: 2;
    border-bottom: 1px solid ${Color.border.medium};
  }

  tbody tr {
    transition: background ${Transition.fast};
  }
  tbody tr:hover {
    background: ${Color.bg.page};
  }
  tbody tr:last-child td { border-bottom: none; }
`

const StickyCol = styled.td<{ $left: number; $th?: boolean }>`
  position: sticky;
  left: ${({ $left }) => $left}px;
  background: inherit;
  z-index: 1;

  /* sticky 列在行 hover 时保持不透明底色 */
  tbody tr & { background: ${Color.bg.card}; }
  tbody tr:hover & { background: ${Color.bg.page}; }
`

const Thumb = styled.div`
  width: 48px;
  height: 48px;
  border-radius: ${Radius.md}px;
  overflow: hidden;
  background: ${Color.bg.page};
  border: 1px solid ${Color.border.light};
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);

  img { width: 100%; height: 100%; object-fit: cover; display: block; }
`

const ProductName = styled.div`
  max-width: 220px;
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.semibold};
  color: ${Color.text.heading};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

const ProductId = styled.div`
  font-size: 11px;
  color: ${Color.text.muted};
  ${Type.tnum}
`

const PlatformHead = styled.div`
  display: flex;
  align-items: center;
  gap: 9px;
  color: ${Color.text.heading};
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.semibold};
  text-transform: none;
  letter-spacing: 0;
`

const PlatformLogo = styled.div`
  width: 30px;
  height: 30px;
  border-radius: 8px;
  overflow: hidden;
  background: ${Color.bg.page};
  border: 1px solid ${Color.border.light};
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: ${FontWeight.bold};
  color: ${Color.text.muted};
  flex-shrink: 0;

  img { width: 100%; height: 100%; object-fit: contain; display: block; }
`

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px); }
  75% { transform: translateX(3px); }
`

const Cell = styled.td<{ $dirty?: boolean; $editing?: boolean; $invalid?: boolean }>`
  min-width: 138px;
  cursor: pointer;
  position: relative;
  transition: background ${Transition.fast}, box-shadow ${Transition.fast};

  &:hover {
    background: ${Color.bg.sunken};
  }

  ${({ $dirty }) =>
    $dirty &&
    `
    background: ${Color.brandSoft};
    box-shadow: inset 0 0 0 1.5px ${Color.brand}, inset 3px 0 0 ${Color.brand};
  `}
  ${({ $editing }) =>
    $editing &&
    `
    box-shadow: inset 0 0 0 2px ${Color.primary}, 0 0 0 3px ${Color.primary}22;
    background: #fff;
  `}
  ${({ $invalid }) =>
    $invalid &&
    `
    animation: ${shake} 0.3s ease;
    box-shadow: inset 0 0 0 2px ${Color.status.error};
  `}
`

const CellInner = styled.div`
  position: relative;
  padding-bottom: 13px;
  min-height: 42px;
`

const Amount = styled.div<{ $dirty?: boolean; $empty?: boolean }>`
  ${Type.tnum}
  font-size: ${FontSize.md}px;
  font-weight: ${FontWeight.semibold};
  color: ${({ $dirty, $empty }) => ($dirty ? Color.brand : $empty ? Color.text.muted : Color.text.heading)};
  display: flex;
  align-items: center;
  gap: 6px;
`

const PrevAmount = styled.div`
  position: absolute;
  left: 0;
  bottom: 0;
  font-size: 10.5px;
  color: ${Color.text.muted};
  text-decoration: line-through;
  ${Type.tnum}
  opacity: 0.75;
`

const StatusDot = styled.span<{ $status?: string | null }>`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: ${({ $status }) =>
    $status === 'done' ? Color.status.success
    : $status === 'executing' ? Color.status.warning
    : $status === 'failed' ? Color.status.error
    : Color.border.medium};
`

const HistoryBtn = styled.button`
  position: absolute;
  right: 0;
  bottom: 0;
  border: none;
  background: none;
  padding: 2px;
  cursor: pointer;
  color: ${Color.text.muted};
  opacity: 0;
  transition: opacity ${Transition.fast};

  ${Cell}:hover & { opacity: 1; }
  &:hover { color: ${Color.primary}; }
  svg { width: 13px; height: 13px; display: block; }
`

const AmountInput = styled.input`
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: ${FontSize.md}px;
  font-weight: ${FontWeight.semibold};
  color: ${Color.text.heading};
  ${Type.tnum}
  padding: 0;
`

const ErrorBar = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: ${Radius.md}px;
  color: ${Color.status.error};
  font-size: ${FontSize.sm}px;
  margin-bottom: ${Spacing.lg}px;
`

const HistoryList = styled.div`
  max-height: 400px;
  overflow-y: auto;
`

const HistoryRow = styled.div`
  display: grid;
  grid-template-columns: 56px 1fr 90px 110px 150px;
  gap: 12px;
  align-items: center;
  padding: 10px 4px;
  font-size: ${FontSize.sm}px;

  & + & { border-top: 1px solid ${Color.border.light}; }
`

const HistoryVersion = styled.span`
  ${Type.tnum}
  font-weight: ${FontWeight.bold};
  color: ${Color.primary};
`

const HistoryAmount = styled.span`
  ${Type.tnum}
  font-weight: ${FontWeight.semibold};
`

const HistoryMeta = styled.span`
  color: ${Color.text.muted};
  font-size: ${FontSize.xs}px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

const StatusText = styled.span<{ $status?: string | null }>`
  font-size: ${FontSize.xs}px;
  color: ${({ $status }) =>
    $status === 'done' ? Color.status.success
    : $status === 'executing' ? Color.status.warning
    : $status === 'failed' ? Color.status.error
    : Color.text.muted};
`

const FooterBar = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: ${Spacing.md}px ${Spacing.xl}px;
`

/* ── 底部悬浮保存条：有待保存改动时滑出 ── */
const saveBarIn = keyframes`
  from { opacity: 0; transform: translate(-50%, 16px); }
  to { opacity: 1; transform: translate(-50%, 0); }
`

const SaveBar = styled.div`
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%);
  z-index: 900;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 12px 10px 20px;
  border-radius: ${Radius.full}px;
  background: rgba(17, 20, 28, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(14px);
  color: #e5e9f0;
  font-size: ${FontSize.sm}px;
  animation: ${saveBarIn} 0.25s ease both;
`

const SaveBarText = styled.span`
  ${Type.tnum}
  display: inline-flex;
  align-items: center;
  gap: 8px;

  b {
    color: #fff;
    font-weight: ${FontWeight.bold};
  }
`

const SaveBarDot = styled.span`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${Color.brand};
  box-shadow: 0 0 8px ${Color.brand};
`

const SaveBarBtn = styled.button<{ $primary?: boolean }>`
  height: 34px;
  padding: 0 18px;
  border-radius: ${Radius.full}px;
  border: 1px solid ${({ $primary }) => ($primary ? 'transparent' : 'rgba(255,255,255,0.2)')};
  background: ${({ $primary }) => ($primary ? `linear-gradient(120deg, ${Color.brand}, #ff6b4a)` : 'transparent')};
  color: ${({ $primary }) => ($primary ? '#fff' : '#c6ccd8')};
  font-size: ${FontSize.sm}px;
  font-weight: ${FontWeight.semibold};
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: opacity ${Transition.fast}, transform ${Transition.fast};

  &:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`

/* ───────────────────────── 逻辑 ───────────────────────── */

const PER_PAGE = 15
const MAX_AMOUNT = 999999.99

const cellKey = (spuId: number, code: string) => `${spuId}:${code}`

function fmtAmount(raw: string | null | undefined): string {
  if (raw == null || raw === '') return ''
  const num = Number(raw)
  if (!Number.isFinite(num)) return String(raw)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 校验编辑输入：非负数字、最多两位小数、不超上限。返回规范化字符串或 null。 */
function normalizeAmount(input: string): string | null {
  const trimmed = input.trim()
  if (trimmed === '') return null
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return null
  const num = Number(trimmed)
  if (!Number.isFinite(num) || num < 0 || num > MAX_AMOUNT) return null
  return num.toFixed(2)
}

export default function AdminAds() {
  const { t, lang } = useTranslation()
  const [rows, setRows] = useState<CampaignRow[]>([])
  const [platforms, setPlatforms] = useState<AdPlatform[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [saving, setSaving] = useState(false)

  /** 待保存修改：key=spu:platform → 金额字符串 */
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [invalidKey, setInvalidKey] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const [historyFor, setHistoryFor] = useState<{ row: CampaignRow; platform: AdPlatform } | null>(null)
  const [historyItems, setHistoryItems] = useState<CampaignHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const dirtyCount = useMemo(() => Object.keys(drafts).length, [drafts])

  const load = useCallback(async (targetPage: number) => {
    setLoading(true)
    setError(false)
    try {
      const data = await adsAPI.getCampaigns({ page: targetPage, per_page: PER_PAGE })
      setRows(data.results || [])
      setPlatforms(data.platforms || [])
      setTotal(data.count || 0)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(page)
  }, [page, load])

  useEffect(() => {
    if (editingKey && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editingKey])

  const displayValue = (row: CampaignRow, code: string): string => {
    const key = cellKey(row.spu_id, code)
    if (key in drafts) return drafts[key]
    return row.cells[code]?.amount ?? ''
  }

  const commitEdit = (row: CampaignRow, code: string, raw: string) => {
    const key = cellKey(row.spu_id, code)
    setEditingKey(null)
    if (raw.trim() === '') {
      // 清空 = 清除修改（未保存时）或恢复只读；不产生 0 投放
      setDrafts((prev) => {
        if (!(key in prev)) return prev
        const next = { ...prev }
        delete next[key]
        return next
      })
      return
    }
    const normalized = normalizeAmount(raw)
    if (normalized == null) {
      setInvalidKey(key)
      toast.warning(t('admin.ads.invalidAmount'))
      window.setTimeout(() => setInvalidKey(null), 400)
      return
    }
    const original = row.cells[code]?.amount
    setDrafts((prev) => {
      const next = { ...prev }
      if (original != null && Number(original) === Number(normalized)) {
        delete next[key]
      } else if (original == null && Number(normalized) === 0) {
        delete next[key]
      } else {
        next[key] = normalized
      }
      return next
    })
  }

  const handleSave = async () => {
    if (dirtyCount === 0 || saving) return
    const items: CampaignSaveItem[] = Object.entries(drafts).map(([key, amount]) => {
      const [spuId, code] = key.split(':')
      const row = rows.find((r) => r.spu_id === Number(spuId))
      return {
        spu_id: Number(spuId),
        platform_code: code,
        amount,
        base_version: row?.cells[code]?.version ?? 0,
      }
    })
    setSaving(true)
    try {
      const res = await adsAPI.saveCampaigns(items)
      toast.success(t('admin.ads.saveSuccess', { count: res.saved?.length ?? items.length }))
      setDrafts({})
      await load(page)
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        toast.error(t('admin.ads.conflict'))
        setDrafts({})
        await load(page)
      } else {
        toast.error(t('admin.ads.saveFailed'))
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDiscard = () => {
    if (dirtyCount === 0) return
    setDrafts({})
    setEditingKey(null)
  }

  const openHistory = async (row: CampaignRow, platform: AdPlatform) => {
    setHistoryFor({ row, platform })
    setHistoryLoading(true)
    setHistoryItems([])
    try {
      const res = await adsAPI.getCampaignHistory(row.spu_id, platform.code)
      setHistoryItems(res.results || [])
    } catch {
      toast.error(t('admin.ads.historyFailed'))
    } finally {
      setHistoryLoading(false)
    }
  }

  const statusLabel = (status?: string | null) =>
    status ? t(`admin.ads.status.${status}`) : ''

  return (
    <Wrap>
      <Head>
        <div>
          <TitleWrap>
            <TitleBadge>
              <Icon name="trending" />
            </TitleBadge>
            <div>
              <Title>{t('admin.ads.title')}</Title>
              <Sub>{t('admin.ads.subtitle')}</Sub>
            </div>
          </TitleWrap>
          {!loading && !error && (
            <StatChips>
              <StatChip>{t('admin.ads.statPlatforms')} <b>{platforms.length}</b></StatChip>
              <StatChip>{t('admin.ads.statProducts')} <b>{total}</b></StatChip>
              {dirtyCount > 0 && (
                <StatChip $accent>{t('admin.ads.statDirty')} <b>{dirtyCount}</b></StatChip>
              )}
            </StatChips>
          )}
        </div>
        <Actions>
          <Btn onClick={handleDiscard} disabled={dirtyCount === 0 || saving}>
            <Icon name="x" />
            {t('admin.ads.discard')}
          </Btn>
          <Btn $primary onClick={handleSave} disabled={dirtyCount === 0 || saving}>
            <Icon name="save" />
            {saving ? t('admin.ads.saving') : t('admin.ads.save')}
            {dirtyCount > 0 && <DirtyChip>{dirtyCount}</DirtyChip>}
          </Btn>
        </Actions>
      </Head>

      {error && (
        <ErrorBar>
          <Icon name="alert" />
          {t('admin.ads.loadError')}
          <Btn onClick={() => load(page)}>{t('promo.retry')}</Btn>
        </ErrorBar>
      )}

      {loading ? (
        <TableCard>
          <div style={{ padding: 24 }}>
            <Skeleton type="table" rows={6} />
          </div>
        </TableCard>
      ) : !error && rows.length === 0 ? (
        <TableCard>
          <Empty title={t('admin.ads.empty')} />
        </TableCard>
      ) : !error ? (
        <>
          <TableCard>
            <Table>
              <thead>
                <tr>
                  <th style={{ width: 64 }}>{t('admin.ads.colImage')}</th>
                  <th>{t('admin.ads.colProduct')}</th>
                  {platforms.map((p) => (
                    <th key={p.code}>
                      <PlatformHead>
                        <PlatformLogo>
                          {p.logo_url ? (
                            <img src={p.logo_url} alt={p.name} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                          ) : (
                            p.name.charAt(0)
                          )}
                        </PlatformLogo>
                        {p.name}
                      </PlatformHead>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.spu_id}>
                    <StickyCol $left={0} style={{ minWidth: 64 }}>
                      <Thumb>
                        <SmartImage
                          src={optionalMediaUrl(row.spu_image)}
                          alt={row.spu_name}
                          loading="lazy"
                          decoding="async"
                        />
                      </Thumb>
                    </StickyCol>
                    <td>
                      <ProductName title={row.spu_name}>
                        {localizedText(lang, row.spu_name, row.spu_name_en, row.spu_name_ar, row.spu_name)}
                      </ProductName>
                      <ProductId>#{row.spu_id}</ProductId>
                    </td>
                    {platforms.map((p) => {
                      const key = cellKey(row.spu_id, p.code)
                      const cell = row.cells[p.code]
                      const isDirty = key in drafts
                      const isEditing = editingKey === key
                      const isInvalid = invalidKey === key
                      const value = displayValue(row, p.code)
                      return (
                        <Cell
                          key={p.code}
                          $dirty={isDirty}
                          $editing={isEditing}
                          $invalid={isInvalid}
                          onClick={() => { if (!isEditing) setEditingKey(key) }}
                        >
                          <CellInner>
                            {isEditing ? (
                              <AmountInput
                                ref={inputRef}
                                defaultValue={value}
                                inputMode="decimal"
                                placeholder="0.00"
                                onClick={(e) => e.stopPropagation()}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') commitEdit(row, p.code, (e.target as HTMLInputElement).value)
                                  if (e.key === 'Escape') setEditingKey(null)
                                }}
                                onBlur={(e) => commitEdit(row, p.code, e.target.value)}
                              />
                            ) : (
                              <Amount $dirty={isDirty} $empty={value === ''}>
                                <StatusDot $status={cell?.status} />
                                {value === '' ? '—' : `$${fmtAmount(value)}`}
                              </Amount>
                            )}
                            {!isEditing && cell?.prev_amount != null && (
                              <PrevAmount>${fmtAmount(cell.prev_amount)}</PrevAmount>
                            )}
                            {!isEditing && (
                              <HistoryBtn
                                title={t('admin.ads.history')}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  openHistory(row, p)
                                }}
                              >
                                <Icon name="clock" />
                              </HistoryBtn>
                            )}
                          </CellInner>
                        </Cell>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableCard>
          <FooterBar>
            <Pagination current={page} total={total} pageSize={PER_PAGE} onChange={setPage} />
          </FooterBar>
        </>
      ) : null}

      {dirtyCount > 0 && (
        <SaveBar>
          <SaveBarText>
            <SaveBarDot />
            {t('admin.ads.pendingChanges')} <b>{dirtyCount}</b>
          </SaveBarText>
          <SaveBarBtn onClick={handleDiscard} disabled={saving}>
            <Icon name="x" />
            {t('admin.ads.discard')}
          </SaveBarBtn>
          <SaveBarBtn $primary onClick={handleSave} disabled={saving}>
            <Icon name="save" />
            {saving ? t('admin.ads.saving') : t('admin.ads.saveNow')}
          </SaveBarBtn>
        </SaveBar>
      )}

      <Modal
        open={historyFor != null}
        title={
          historyFor
            ? `${localizedText(lang, historyFor.row.spu_name, historyFor.row.spu_name_en, historyFor.row.spu_name_ar, historyFor.row.spu_name)} · ${historyFor.platform.name} · ${t('admin.ads.history')}`
            : ''
        }
        footer={null}
        onClose={() => setHistoryFor(null)}
      >
        {historyLoading ? (
          <Skeleton type="table" rows={3} />
        ) : historyItems.length === 0 ? (
          <Empty title={t('admin.ads.historyEmpty')} />
        ) : (
          <HistoryList>
            {historyItems.map((item) => (
              <HistoryRow key={item.id}>
                <HistoryVersion>v{item.version}</HistoryVersion>
                <HistoryAmount>${fmtAmount(item.amount)}</HistoryAmount>
                <StatusText $status={item.status}>{statusLabel(item.status)}</StatusText>
                <HistoryMeta>{item.operator || '-'}</HistoryMeta>
                <HistoryMeta>{new Date(item.created_at).toLocaleString()}</HistoryMeta>
              </HistoryRow>
            ))}
          </HistoryList>
        )}
      </Modal>
    </Wrap>
  )
}
