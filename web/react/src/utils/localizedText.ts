/**
 * 多语言文本工具：根据当前界面语言选择商品/分类的多语言字段。
 *
 * 数据模型支持多语言字段（name_en / name_zh / name_ar 等）。
 * - 界面语言为英文（en-US）且存在英文字段时，返回英文内容；
 * - 界面语言为中文（zh-CN）且存在中文字段时，返回中文内容；
 * - 界面语言为阿拉伯语（ar）且存在阿拉伯语内容时，返回阿拉伯语内容；
 * - 否则回退到默认语言字段（name，通常为第二种兜底）。
 */
import type { Language } from '../i18n'
import type { PublicCategory } from '../api/public'

/**
 * 根据语言选择本地化文本。
 * @param lang 当前界面语言
 * @param defaultText 默认语言文本（如 name）
 * @param enText 英文文本（如 name_en），可为空
 * @param arText 阿拉伯语文本（如 name_ar），可为空
 */
export function localizedText(
  lang: Language,
  defaultText: string,
  enText?: string | null,
  arText?: string | null,
  zhText?: string | null,
): string {
  if (lang === 'en-US' && enText && enText.trim()) {
    return enText
  }
  if (lang === 'zh-CN' && zhText && zhText.trim()) {
    return zhText
  }
  if (lang === 'ar' && arText && arText.trim()) {
    return arText
  }
  return defaultText
}

/**
 * 分类名本地化：根据界面语言返回分类的多语言名称。
 * @param lang 当前界面语言
 * @param cat 分类节点（含 name / name_en / name_zh / name_ar）
 * @param name 直接传入的名称（回避类型依赖）
 */
export function localizeCategory(
  lang: Language,
  cat: { name: string; name_en?: string; name_zh?: string; name_ar?: string } | null | undefined,
): string {
  if (!cat) return ''
  return localizedText(lang, cat.name, cat.name_en, cat.name_ar, cat.name_zh)
}

export function categoryLocalizedName(
  lang: Language,
  cat: PublicCategory | null | undefined,
): string {
  return localizeCategory(lang, cat)
}