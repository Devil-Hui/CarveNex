import { createContext, useContext, useState, useCallback, useMemo, useEffect, type ReactNode } from 'react'
import en, { type Translations } from './en'
import zhCN from './zh-CN'
import ar from './ar'

export type Language = 'en-US' | 'zh-CN' | 'ar'

const LANGUAGE_KEY = 'carvenex_lang'

const packs: Record<Language, Translations> = {
  'en-US': en,
  'zh-CN': zhCN as unknown as Translations,
  'ar': ar as unknown as Translations,
}

function getInitialLang(): Language {
  try {
    const stored = localStorage.getItem(LANGUAGE_KEY)
    if (stored === 'en-US' || stored === 'zh-CN' || stored === 'ar') return stored
  } catch { /* noop */ }
  // Default to en-US
  return 'en-US'
}

interface I18nContextValue {
  lang: Language
  setLang: (lang: Language) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function resolve(obj: Record<string, unknown>, path: string): string {
  const keys = path.split('.')
  let current: unknown = obj
  for (const k of keys) {
    if (current == null || typeof current !== 'object') return path
    current = (current as Record<string, unknown>)[k]
  }
  return typeof current === 'string' ? current : path
}

// 阿拉伯语为 RTL（从右往左）布局
const RTL_LANGS: Language[] = ['ar']

function applyDir(lang: Language) {
  try {
    const isRtl = RTL_LANGS.includes(lang)
    document.documentElement.setAttribute('dir', isRtl ? 'rtl' : 'ltr')
    document.documentElement.setAttribute('lang', lang)
  } catch { /* noop */ }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(getInitialLang)

  // 初始化时应用方向（RTL/LTR）
  useEffect(() => { applyDir(lang) }, [lang])

  const setLang = useCallback((lang: Language) => {
    setLangState(lang)
    applyDir(lang)
    try { localStorage.setItem(LANGUAGE_KEY, lang) } catch { /* noop */ }
  }, [])

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      // 阿拉伯语语言包可能未完全翻译，缺失 key 回退到英文
      let str = resolve(packs[lang] as unknown as Record<string, unknown>, key)
      if (str === key && lang !== 'en-US') {
        str = resolve(packs['en-US'] as unknown as Record<string, unknown>, key)
      }
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          str = str.replace(new RegExp('\\$\\{' + k + '\\}', 'g'), String(v))
        }
      }
      return str
    },
    [lang],
  )

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  )
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider')
  return ctx
}

export { packs }