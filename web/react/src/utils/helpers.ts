export function formatPrice(price: number): string {
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * 管理后台统一日期时间格式：YYYY-MM-DD HH:mm:ss
 * 避免各页面使用浏览器 locale 导致 2026/8/19 与 2026/08/23 不一致。
 */
export function formatDateTime(dateInput: string | number | Date | undefined | null): string {
  if (!dateInput) return '-'
  const date = typeof dateInput === 'object' && dateInput !== null ? dateInput : new Date(dateInput)
  if (Number.isNaN(date.getTime())) return String(dateInput)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/**
 * 管理后台统一日期格式：YYYY-MM-DD（用于有效期、起止日期等不需要时刻的场景）
 */
export function formatDate(dateInput: string | number | Date | undefined | null): string {
  if (!dateInput) return '-'
  const date = typeof dateInput === 'object' && dateInput !== null ? dateInput : new Date(dateInput)
  if (Number.isNaN(date.getTime())) return String(dateInput)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export function generateId(): number {
  return Date.now() + Math.random()
}

export function validateEmail(email: string): boolean {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export function validatePhone(phone: string): boolean {
  const re = /^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/
  return re.test(phone)
}

// 与后端 USERS_SETTINGS.PASSWORD_MIN_LENGTH 保持一致
//（backend/project/config/settings/base.py）；前端不得放宽，否则
// 表单校验通过但后端注册/改密被拒，造成用户困惑。
export const PASSWORD_MIN_LENGTH = 8

export function validatePassword(password: string): boolean {
  return password.length >= PASSWORD_MIN_LENGTH
}
