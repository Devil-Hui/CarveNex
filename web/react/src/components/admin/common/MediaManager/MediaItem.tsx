/** MediaItem —— 单个媒体项（缩略图 + hover 操作浮层：编辑 / 删除）。
 * 支持两种数据源：StagedMediaItem（创建模式暂存）和 ProductMediaItem（编辑模式已保存）。
 * 交互：点击视频/图片 → 打开大图预览（视频直接播放）；长按 2s → 进入拖动排序。
 */
import { useRef } from 'react'
import * as S from './MediaManager.styles'
import type { StagedMediaItem } from '../../../../utils/mediaStaging'
import type { ProductMediaItem } from '../../../../api/admin'
import { resolveMediaUrl } from '../../../../api/chat'
import { useTranslation } from '@/i18n'

interface Props {
  item: StagedMediaItem | ProductMediaItem
  index: number
  onRemove: (id: number) => void
  onEdit?: (item: ProductMediaItem) => void
  /** 原地重新裁剪（仅已保存图片） */
  onRecrop?: (item: ProductMediaItem) => void
  /** 点击媒体项打开预览（视频直接播放） */
  onPreview?: (url: string, kind: 'image' | 'video', name: string) => void
  /** 拖拽激活态（长按 2s 后置真，视觉反馈 + 允许拖动） */
  dragActive?: boolean
  /** 指针按下：交给父组件启动长按计时 */
  onDragHandleDown?: (e: React.PointerEvent, index: number) => void
}

/** 类型守卫：判断是否为已保存媒体项（后端返回） */
function isSavedMedia(item: StagedMediaItem | ProductMediaItem): item is ProductMediaItem {
  return 'media_type' in item
}

export default function MediaItem({ item, index, onRemove, onEdit, onRecrop, onPreview, dragActive, onDragHandleDown }: Props) {
  const { t } = useTranslation()
  const saved = isSavedMedia(item)
  const mediaType = saved ? item.media_type : (item as StagedMediaItem).mediaType
  const id = saved ? item.id : (item as StagedMediaItem).id
  const fileName = saved ? (item.alt_text || `媒体#${item.id}`) : (item as StagedMediaItem).fileName
  // 区分「普通点击（预览）」与「长按 2s 拖动结束后的点击（忽略）」
  const pressStartRef = useRef(0)

  // 缩略图 src（编辑模式需 resolveMediaUrl 把 /media/ 相对路径转为后端绝对 URL）
  let src: string
  if (saved) {
    const mediaItem = item as ProductMediaItem
    // 弹窗缩略图用 list(400px) 而非 thumb(200px)，Retina 屏放大不糊（兼顾清晰与带宽）
    const rawUrl = mediaItem.media_type === 'image'
      ? (mediaItem.list_url || mediaItem.large_url || mediaItem.thumb_url || '')
      : (mediaItem.video_list_url || mediaItem.video_large_url || mediaItem.video_thumb_url || mediaItem.video_url || '')
    src = resolveMediaUrl(rawUrl) || rawUrl
  } else {
    const stagedItem = item as StagedMediaItem
    if (stagedItem.mediaType === 'image') {
      src = stagedItem.previewDataUrl || ''
    } else {
      // 视频：previewDataUrl 若是 blob:（VideoUploadDialog 写入的 session 级 blob URL），
      // 持久化到 IndexedDB 后刷新页面即失效 → net::ERR_FILE_NOT_FOUND。
      // 因此一律用 videoBlob（File 会随 IndexedDB 持久化）重新生成 object URL。
      const videoBlobUrl = stagedItem.videoBlob
        ? URL.createObjectURL(stagedItem.videoBlob)
        : ''
      src = stagedItem.previewDataUrl?.startsWith('blob:')
        ? videoBlobUrl || ''
        : stagedItem.previewDataUrl || videoBlobUrl
    }
  }

  const handlePreviewClick = () => {
    // 长按拖动结束后的 click（距按下 >1.5s）忽略，避免误弹预览
    if (Date.now() - pressStartRef.current > 1500) return
    // 视频：优先用原视频 URL 播放；图片：用大图/原图预览（避免 200px 缩略图放大糊）
    let playUrl = src
    if (mediaType === 'video') {
      const videoUrl = saved
        ? resolveMediaUrl((item as ProductMediaItem).video_url || '') || (item as ProductMediaItem).video_url
        : (item as StagedMediaItem).videoBlob ? URL.createObjectURL((item as StagedMediaItem).videoBlob!) : src
      if (videoUrl) playUrl = videoUrl
    } else if (saved) {
      const mediaItem = item as ProductMediaItem
      const rawUrl = mediaItem.original_url || mediaItem.large_url || mediaItem.list_url || mediaItem.thumb_url || ''
      playUrl = resolveMediaUrl(rawUrl) || rawUrl
    } else {
      const stagedItem = item as StagedMediaItem
      const big = stagedItem.originalBlob
        ? URL.createObjectURL(stagedItem.originalBlob)
        : stagedItem.largeBlob
          ? URL.createObjectURL(stagedItem.largeBlob)
          : ''
      if (big) playUrl = big
    }
    onPreview?.(playUrl, mediaType, fileName)
  }

  return (
    <S.ItemWrap
      title={fileName}
      $dragActive={dragActive}
      onPointerDown={(e) => {
        // 拖拽句柄：左键/触屏按下时交给父组件长按计时（点击预览与长按拖动互不冲突）
        if (e.button === 0 || e.pointerType !== 'mouse') {
          pressStartRef.current = Date.now()
          onDragHandleDown?.(e, index)
        }
      }}
      onClick={handlePreviewClick}
    >
      {/* 视频：若已保存首帧（video_thumb_url），优先以该首帧图作为显示封面；
          否则回退到 <video preload="metadata"> 由播放器呈现首帧。 */}
      {mediaType === 'image' ? (
        <S.ItemImg src={src} alt={fileName} />
      ) : saved && (item as ProductMediaItem).video_thumb_url ? (
        <S.ItemImg
          src={resolveMediaUrl((item as ProductMediaItem).video_thumb_url || '') || (item as ProductMediaItem).video_thumb_url}
          alt={fileName}
        />
      ) : (
        <S.ItemVideo src={src} muted preload="metadata" playsInline />
      )}

      {/* 视频点击提示（首次上传后点击即可直接播放观看） */}
      {mediaType === 'video' && (
        <S.VideoPlayBadge title={t('admin.mediaManager.play')}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="#fff" aria-hidden>
            <path d="M8 5v14l11-7z" />
          </svg>
        </S.VideoPlayBadge>
      )}

      {/* hover 操作浮层：重新裁剪 / 编辑（仅已保存项）/ 删除 */}
      <S.HoverOverlay className="hover-overlay">
        {saved && mediaType === 'image' && onRecrop && (
          <S.OverlayBtn
            type="button"
            title={t('admin.mediaManager.recrop')}
            onClick={(e) => {
              e.stopPropagation()
              onRecrop(item as ProductMediaItem)
            }}
          >
            ✂
          </S.OverlayBtn>
        )}
        {saved && onEdit && (
          <S.OverlayBtn
            type="button"
            title={t('common.edit')}
            onClick={(e) => {
              e.stopPropagation()
              onEdit(item as ProductMediaItem)
            }}
          >
            ✎
          </S.OverlayBtn>
        )}
        <S.OverlayBtn
          type="button"
          title={t('common.delete')}
          onClick={(e) => {
            e.stopPropagation()
            if (id != null) onRemove(id)
          }}
        >
          ×
        </S.OverlayBtn>
      </S.HoverOverlay>

      {/* 状态点（已保存项显示审核状态） */}
      {saved && (item as ProductMediaItem).status !== 'active' && (
        <S.StatusDot $status={(item as ProductMediaItem).status} />
      )}

      {/* 视频角标（图片序号/主图徽章由外层网格负责） */}
      {mediaType === 'video' && (
        <S.ItemBadge $type="video">{t('admin.mediaManager.videoBadge')}</S.ItemBadge>
      )}
    </S.ItemWrap>
  )
}