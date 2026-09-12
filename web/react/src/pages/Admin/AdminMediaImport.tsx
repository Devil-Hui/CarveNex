// TypeScript strict mode enabled
import { useState, useRef, useCallback } from 'react'
import styled from 'styled-components'
import { Color, Radius, Spacing, FontSize } from '../../theme/tokens'
import { SecondaryBtn, PrimaryBtn } from '../../components/admin/common/ui'
import { post } from '../../api/request'
import { Icon } from '../../components/admin/common/Icon'
import PageHeader from '../../components/admin/common/PageHeader'
import ErrorRetry from '../../components/admin/common/ErrorRetry'
import { useTranslation } from '../../i18n'

// ── Styled Components ──

const PageContainer = styled.div`
  padding: 0;
`

const Card = styled.div`
  background: ${Color.bg.card};
  border: 1px solid ${Color.border.light};
  border-radius: ${Radius.sm}px;
  padding: ${Spacing.xxl}px;
`

const UploadArea = styled.div<{ $isDragging: boolean }>`
  border: 2px dashed ${({ $isDragging }) => ($isDragging ? Color.primary : '#ddd')};
  border-radius: 6px;
  padding: 48px 24px;
  text-align: center;
  background: ${({ $isDragging }) => ($isDragging ? '#f5f5f5' : '#f5f5f5')};
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: ${Color.primary};
    background: ${Color.primaryLight};
  }
`

const UploadIcon = styled.div`
  font-size: 40px;
  margin-bottom: 12px;
  color: ${Color.border.dark};
`

const UploadTitle = styled.p`
  font-size: ${FontSize.md}px;
  color: ${Color.primaryHover};
  margin: 0 0 6px 0;
  font-weight: 500;
`

const UploadHint = styled.p`
  font-size: ${FontSize.xs}px;
  color: ${Color.text.muted};
  margin: 0;
`

const HiddenInput = styled.input`
  display: none;
`

const ParsingOverlay = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
`

const Spinner = styled.div`
  width: 36px;
  height: 36px;
  border: 3px solid ${Color.border.light};
  border-top-color: ${Color.primary};
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`

const ParsingText = styled.p`
  font-size: ${FontSize.base}px;
  color: ${Color.text.secondary};
  margin: 0;
`

// ── Crop 选择 ──

const OptionsRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 20px;

  @media (max-width: 600px) {
    grid-template-columns: 1fr;
  }
`

const Field = styled.div`
  margin-bottom: 0;
`

const Label = styled.label`
  display: block;
  font-size: ${FontSize.sm}px;
  color: ${Color.text.secondary};
  margin-bottom: 6px;
`

const Select = styled.select`
  width: 100%;
  padding: 9px 12px;
  border: 1px solid ${Color.border.medium};
  border-radius: ${Radius.md}px;
  font-size: ${FontSize.base}px;
  box-sizing: border-box;
  color: ${Color.text.body};
  background: ${Color.bg.card};
`

// ── 结果展示 ──

const ResultSection = styled.div`
  margin-top: 20px;
`

const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
`

const ResultTitle = styled.h3`
  font-size: ${FontSize.base}px;
  font-weight: 600;
  color: ${Color.primaryHover};
  margin: 0;
`

const ResultCount = styled.span`
  font-size: ${FontSize.xs}px;
  color: ${Color.text.muted};
  background: ${Color.primaryLight};
  padding: 2px 10px;
  border-radius: 10px;
`

const ResultTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${FontSize.xs}px;
  background: ${Color.bg.card};
  border: 1px solid ${Color.border.light};
  border-radius: ${Radius.sm}px;
  overflow: hidden;
`

const ResultTh = styled.th`
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #8a8175;
  background: rgba(26, 23, 18, 0.03);
  border-bottom: 1px solid ${Color.border.light};
  white-space: nowrap;
  font-size: ${FontSize.xs}px;
`

const ResultTd = styled.td`
  padding: 8px 12px;
  color: ${Color.primaryHover};
  border-bottom: 1px solid ${Color.border.light};
`

const ResultWrapper = styled.div`
  max-height: 360px;
  overflow: auto;
`

const SkippedBox = styled.div`
  margin-top: 12px;
  font-size: ${FontSize.xs}px;
  color: ${Color.text.muted};
  background: rgba(26, 23, 18, 0.03);
  border-radius: ${Radius.sm}px;
  padding: 10px 14px;
`

const ButtonRow = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 16px;
`

const ResultCard = styled.div<{ $success: boolean }>`
  padding: 20px 24px;
  border-radius: ${Radius.sm}px;
  background: ${({ $success }) => ($success ? '#e8f5e9' : '#fde8e8')};
  border: 1px solid ${({ $success }) => ($success ? '#c8e6c9' : '#f5c6cb')};
  margin-top: 20px;
  text-align: center;
`

const ResultTitleText = styled.p<{ $success: boolean }>`
  font-size: ${FontSize.md}px;
  font-weight: 600;
  color: ${({ $success }) => ($success ? '#2e7d32' : '#c62828')};
  margin: 0 0 8px 0;
`

const ResultMessage = styled.p`
  font-size: ${FontSize.sm}px;
  color: ${Color.text.secondary};
  margin: 0 0 12px 0;
`

// ── Types ──

type PageState = 'upload' | 'importing' | 'result'

interface FolderResult {
  folder: string
  images: number
  videos: number
  errors: string[]
}

interface ImportResponse {
  message?: string
  processed_folders: number
  imported_folders: number
  total_images: number
  total_videos: number
  skipped: string[]
  details: FolderResult[]
}

// ── Component ──

export default function AdminMediaImport() {
  const { t } = useTranslation()
  const [pageState, setPageState] = useState<PageState>('upload')
  const [fileName, setFileName] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResponse | null>(null)
  const [resultError, setResultError] = useState<string | null>(null)
  const [crop, setCrop] = useState('1:1')

  const fileInputRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => {
    setPageState('upload')
    setFileName('')
    setFile(null)
    setError(null)
    setResult(null)
    setResultError(null)
  }, [])

  // ── 文件选择 ──
  const handleSelected = useCallback((selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
      setError(t('admin.mediaImport.invalidZip'))
      return
    }
    setFileName(selectedFile.name)
    setFile(selectedFile)
    setError(null)
    setResult(null)
    setResultError(null)
    setPageState('upload')
  }, [t])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) handleSelected(droppedFile)
  }

  const handleClickUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) handleSelected(selectedFile)
  }

  // ── 导入 ──
  const handleImport = async () => {
    if (!file) return
    setPageState('importing')
    setError(null)
    setResultError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('crop', crop)
      const res = (await post('/goods/spu/import/media-zip', formData)) as ImportResponse
      setResult(res)
      setPageState('result')
    } catch (err: unknown) {
      setResultError(err instanceof Error ? err.message : t('import.mediaImport.importFailed'))
      setPageState('result')
    }
  }

  // ── Render ──

  return (
    <PageContainer>
      <PageHeader
        title={t('import.mediaImport.title')}
        breadcrumb={[{ label: t('import.mediaImport.subtitle') }, { label: t('import.mediaImport.title') }]}
      />

      <Card>
        {/* Upload */}
        {pageState === 'upload' && (
          <>
            <UploadArea
              $isDragging={isDragging}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleClickUpload}
            >
              <UploadIcon><Icon name="upload" size={32} /></UploadIcon>
              <UploadTitle>
                {fileName || t('import.mediaImport.dropZone')}
              </UploadTitle>
              <UploadHint>{t('import.mediaImport.supportedFormats')}</UploadHint>
              <HiddenInput
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleFileChange}
              />
            </UploadArea>

            {/* 裁切比例 */}
            <OptionsRow>
              <Field>
                <Label>{t('import.mediaImport.crop')}</Label>
                <Select value={crop} onChange={(e) => setCrop(e.target.value)}>
                  <option value="1:1">{t('import.mediaImport.cropSquare')}</option>
                  <option value="4:3">4:3</option>
                  <option value="3:4">3:4</option>
                  <option value="none">{t('import.mediaImport.cropNone')}</option>
                </Select>
              </Field>
            </OptionsRow>

            <ButtonRow>
              <PrimaryBtn onClick={handleImport} disabled={!file}>
                {t('import.mediaImport.confirmImport')}
              </PrimaryBtn>
            </ButtonRow>
            {error && (
              <div style={{ marginTop: 16 }}>
                <ErrorRetry message={t('import.mediaImport.parseError')} detail={error} onRetry={reset} />
              </div>
            )}
          </>
        )}

        {/* Importing */}
        {pageState === 'importing' && (
          <ParsingOverlay>
            <Spinner />
            <ParsingText>{t('import.mediaImport.importing')}</ParsingText>
          </ParsingOverlay>
        )}

        {/* Result */}
        {pageState === 'result' && (
          <>
            {resultError ? (
              <ResultCard $success={false}>
                <ResultTitleText $success={false}>{t('import.mediaImport.importFailedStatus')}</ResultTitleText>
                <ResultMessage>{resultError}</ResultMessage>
                <PrimaryBtn onClick={reset}>{t('import.mediaImport.reselectFile')}</PrimaryBtn>
              </ResultCard>
            ) : result && (
              <ResultSection>
                <ResultHeader>
                  <ResultTitle>{t('import.mediaImport.resultTitle')}</ResultTitle>
                  <ResultCount>
                    {t('import.mediaImport.resultCount')
                      .replace('{images}', String(result.total_images))
                      .replace('{videos}', String(result.total_videos))}
                  </ResultCount>
                </ResultHeader>

                <ResultWrapper>
                  <ResultTable>
                    <thead>
                      <tr>
                        <ResultTh>{t('import.mediaImport.colFolder')}</ResultTh>
                        <ResultTh>{t('import.mediaImport.colImages')}</ResultTh>
                        <ResultTh>{t('import.mediaImport.colVideos')}</ResultTh>
                        <ResultTh>{t('import.mediaImport.colErrors')}</ResultTh>
                      </tr>
                    </thead>
                    <tbody>
                      {(result.details || []).map((d, idx) => (
                        <tr key={idx}>
                          <ResultTd>{d.folder}</ResultTd>
                          <ResultTd>{d.images}</ResultTd>
                          <ResultTd>{d.videos}</ResultTd>
                          <ResultTd style={{ color: d.errors?.length ? '#c62828' : '#2e7d32' }}>
                            {d.errors?.length ? d.errors.join('; ') : '✓'}
                          </ResultTd>
                        </tr>
                      ))}
                    </tbody>
                  </ResultTable>
                </ResultWrapper>

                {(result.skipped || []).length > 0 && (
                  <SkippedBox>
                    <strong>{t('import.mediaImport.skipped')}</strong>{' '}
                    {result.skipped.join(', ')}
                  </SkippedBox>
                )}

                <ButtonRow>
                  <PrimaryBtn onClick={reset}>{t('import.mediaImport.continueImport')}</PrimaryBtn>
                </ButtonRow>
              </ResultSection>
            )}
          </>
        )}
      </Card>
    </PageContainer>
  )
}