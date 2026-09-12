/**
 * 多语言文本工具：根据当前界面语言选择商品的多语言字段。
 *
 * 商品数据模型支持多语言字段（name_en / description_en / name_ar / description_ar）。
 * - 界面语言为英文（en-US）且存在英文字段时，返回英文内容；
 * - 界面语言为阿拉伯语（ar）且存在阿拉伯语字段时，返回阿拉伯语内容；
 * - 否则回退到默认语言字段（name / description，通常为中文）。
 */
import type { Language } from '../i18n'

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
): string {
  if (lang === 'en-US' && enText && enText.trim()) {
    return enText
  }
  if (lang === 'ar' && arText && arText.trim()) {
    return arText
  }
  return defaultText
}