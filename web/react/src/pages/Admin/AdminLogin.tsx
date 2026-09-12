import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import styled from 'styled-components'
import { useAdminAuth } from '../../store/AdminAuthContext'
import { useTranslation, LanguageSwitch } from '../../i18n'
import { post, ensureCSRFCookie } from '../../api/request'
import { Color, Shadow } from '../../theme/tokens'

/* ── 配色统一取自 theme 令牌（与商城 C 端同源，改令牌即联动）── */
const CREAM = Color.bg.page
const INK = Color.text.primary
const MUTED = Color.text.muted
const CLAY = Color.primary
const LINE = Color.border.light

const Container = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: ${CREAM};
  padding: 2rem 1rem;
  overflow: hidden;

  /* soft decorative serif watermark */
  &::before {
    content: 'C';
    position: absolute;
    right: -2rem;
    bottom: -6rem;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 26rem;
    line-height: 1;
    color: rgba(14, 16, 19, 0.035);
    pointer-events: none;
    user-select: none;
  }
`

const Card = styled.div`
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 48px 40px 40px;
  background: ${Color.bg.card};
  border: 1px solid ${LINE};
  border-radius: 20px;
  box-shadow: 0 18px 50px -24px rgba(14, 16, 19, 0.18);
`

const Brand = styled.h1`
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 2rem;
  font-weight: 600;
  letter-spacing: -0.5px;
  color: ${INK};
  text-align: center;
  margin: 0 0 6px;
  span { color: ${CLAY}; }
`

const Subtitle = styled.p`
  text-align: center;
  color: ${MUTED};
  font-size: 0.875rem;
  margin: 0 0 28px;
`

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 14px;
`

const Input = styled.input`
  height: 46px;
  padding: 0 16px;
  border: 1px solid ${LINE};
  border-radius: 10px;
  font-size: 0.938rem;
  color: ${INK};
  background: ${Color.bg.card};
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;

  &:focus {
    border-color: ${CLAY};
    box-shadow: ${Shadow.focus};
  }

  &::placeholder {
    color: ${Color.text.muted};
  }
`

const Button = styled.button<{ $loading?: boolean }>`
  height: 46px;
  border: none;
  border-radius: 9999px;
  background: ${CLAY};
  color: ${Color.text.inverse};
  font-size: 0.938rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: ${({ $loading }) => ($loading ? 'not-allowed' : 'pointer')};
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, opacity 0.2s ease;
  opacity: ${({ $loading }) => ($loading ? 0.75 : 1)};

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 10px 24px -10px rgba(14, 16, 19, 0.5);
  }

  &:active:not(:disabled) {
    transform: translateY(0) scale(0.99);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
`

const ErrorText = styled.p`
  color: ${Color.status.error};
  font-size: 0.813rem;
  text-align: center;
  margin: 0;
`

export default function AdminLogin() {
  const { t } = useTranslation()
  const { isAuthenticated, login } = useAdminAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/admin/products" replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      setError(t('admin.login.passwordRequired'))
      return
    }
    setError('')
    setLoading(true)
    try {
      const ok = await login(username, password)
      if (ok) {
        navigate('/admin/products', { replace: true })
      } else {
        setError(t('admin.login.invalidCredentials'))
      }
    } catch (err: unknown) {
      // 展示后端具体失败原因（用户名/密码错误、非管理员等）
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || t('admin.login.invalidCredentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container>
      <Card>
        <Brand>Carve<span>Nex</span></Brand>
        <Subtitle>{t('admin.login.subtitle')}</Subtitle>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
          <LanguageSwitch position="login" />
        </div>
        <Form onSubmit={handleSubmit}>
          <Input
            type="text"
            placeholder={t('admin.login.username')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input
            type="password"
            placeholder={t('admin.login.password')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <ErrorText>{error}</ErrorText>}
          <Button
            type="submit"
            $loading={loading}
            disabled={!username || !password || loading}
          >
            {loading ? t('admin.login.signingIn') : t('admin.login.signIn')}
          </Button>
        </Form>
      </Card>
    </Container>
  )
}