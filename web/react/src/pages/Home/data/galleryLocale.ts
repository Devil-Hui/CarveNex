/**
 * 场景画廊视频标题三语映射表。
 *
 * 说明：scenarioGallery.ts 由脚本自动生成，其中视频 `id` 是对文件名 slug 化
 * 的截断结果（≤48 字符），存在大量碰撞（同一 id 对应多个不同文件，且非 ASCII
 * 文件名被替换为 video-N 占位符），因此不能用 id 作为映射键。
 *
 * 这里统一使用「视频文件名去掉扩展名后的小写规范化键」作为映射键——
 * flatten 后的每张卡片都能从视频 URL 的唯一 basename 推导出该键，天然避免碰撞。
 *
 * 判定顺序（在 ScenarioGallery 中使用）：
 *   1. 命中本表 → 取对应语言标题
 *   2. 未命中（新增本地上传视频等）→ 回退到原始 title
 */
export interface GalleryTitle {
  en: string
  zh: string
  ar: string
}

type GalleryVideo = GalleryTitle

export const galleryVideoTitles: Record<string, GalleryVideo> = {
  '多场景应用': {
    en: 'Multi-scene showcase',
    zh: '多场景应用',
    ar: 'عرض متعدد المشاهد',
  },
  'laserpecker2lasercutlaserengravinglasermachineleathercraftonsitesouvenirsmallbusiness': {
    en: 'Leather crafts & souvenir shop',
    zh: '皮革工艺品与纪念品店',
    ar: 'مشغولات جلدية ومتجر هدايا',
  },
  'personalizeshoeswithlaserpeckerlp5': {
    en: 'Personalize shoes with LP5',
    zh: 'LP5 定制个性化鞋子',
    ar: 'تخصيص الأحذية مع LP5',
  },
  'thebestgiftsayswethoughtofyouengravedbylp4backtoschoollaserpeckergiftideas': {
    en: 'The best gift — engraved by LP4',
    zh: '最好的礼物——LP4 雕刻',
    ar: 'أفضل هدية — نقش بواسطة LP4',
  },
  'backtoschoolshoppinglistbutmakeitpersonallaserpeckerschoolsupplies': {
    en: 'Back-to-school personalized',
    zh: '开学季个性定制',
    ar: 'تخصيص العودة للمدارس',
  },
  'createstampwithlaserpeckerlp5': {
    en: 'Create a stamp with LP5',
    zh: '用 LP5 制作印章',
    ar: 'اصنع ختمًا مع LP5',
  },
  'fastengravingontheswitchwithlaserpeckerlp2': {
    en: 'Fast engraving on a Switch',
    zh: 'Switch 机身快速雕刻',
    ar: 'نقش سريع على جهاز الألعاب',
  },
  '材料塑料': {
    en: 'Plastic',
    zh: '材料（塑料）',
    ar: 'بلاستيك',
  },
  'createoneofakindclotheswithlaserpeckerlp4': {
    en: 'One-of-a-kind clothes with LP4',
    zh: '用 LP4 打造独一无二的衣物',
    ar: 'ملابس فريدة مع LP4',
  },
  'doneinjust10secondslaserengravingontowelwithlaserpeckerlp5': {
    en: 'Towel engraving in 10 seconds',
    zh: '10 秒毛巾雕刻',
    ar: 'نقش على المنشفة في ١٠ ثوانٍ',
  },
  'personalizetowelswiththelaserpeckerlp4fasteasy': {
    en: 'Personalize towels — fast & easy',
    zh: '毛巾个性化——快速简便',
    ar: 'تخصيص المناشف — بسرعة وسهولة',
  },
  '材料布料': {
    en: 'Fabric',
    zh: '材料（布料）',
    ar: 'قماش',
  },
  'laserengravingpictureonwoodenboardwithlaserpecker2s2gvok4paucf137': {
    en: 'Picture on wooden board',
    zh: '木板上的人像照片雕刻',
    ar: 'نقش صورة على لوح خشبي',
  },
  'laserpeckerlp1plusinactionfullyupgradedstillportable': {
    en: 'LP1 Plus in action',
    zh: 'LP1 Plus 实战演示',
    ar: 'LP1 Plus أثناء العمل',
  },
  'laserengravedfootballfieldsnackboardwithlaserpeckerlx2': {
    en: 'Football-field snack board',
    zh: '足球场主题餐盘',
    ar: 'لوح تقديم بتصميم ملعب كرة',
  },
  'customizedcoffeejarwithlaserpeckerlp5': {
    en: 'Custom coffee jar with LP5',
    zh: '用 LP5 定制咖啡罐',
    ar: 'جرة قهوة مخصصة مع LP5',
  },
  'glassengravingwithlaserpeckerlp4androtarytool': {
    en: 'Glass engraving with rotary',
    zh: '玻璃旋转雕刻',
    ar: 'نقش الزجاج بالأداة الدوارة',
  },
  'stone3dembossingwithlaserpeckerlp51': {
    en: 'Stone 3D embossing',
    zh: '石板 3D 浮雕',
    ar: 'نقش بارز ثلاثي الأبعاد على الحجر',
  },
  '3dembossingabrasscoinwiththelaserpeckerlp5': {
    en: '3D emboss a brass coin',
    zh: '黄铜硬币 3D 浮雕',
    ar: 'نقش عملة نحاسية بارزة',
  },
  'colorengravingwithlaserpeckerlp4': {
    en: 'Color engraving with LP4',
    zh: '用 LP4 彩色雕刻',
    ar: 'نقش ملون مع LP4',
  },
  'customnewyearthemeturnblerwithlaserpeckerlp5': {
    en: 'New-year tumbler with LP5',
    zh: '新年主题随行杯',
    ar: 'كوب مخصص برأس السنة مع LP5',
  },
  'deepengravedbuttonswithlaserpeckerlp5': {
    en: 'Deep-engraved buttons',
    zh: '深浮雕纽扣',
    ar: 'أزرار بنقش عميق',
  },
  'engravingwiththelaserpecker4': {
    en: 'Engraving with LaserPecker 4',
    zh: '用 LaserPecker 4 雕刻',
    ar: 'نقش مع LaserPecker 4',
  },
  'laserpecker2customengravedtumblerdiyengravingfullreviewcomingsoon': {
    en: 'Custom tumbler — DIY review',
    zh: '定制随行杯评测',
    ar: 'كوب مخصص — مراجعة DIY',
  },
  'laserpeckerlp2plusdiyhalloweencupthatglows': {
    en: 'Halloween cup that glows',
    zh: '发光万圣节杯子',
    ar: 'كوب هالوين مضيء',
  },
  'statueoflibertycoinembossingwithlaserpeckerlp5': {
    en: 'Statue of Liberty coin',
    zh: '自由女神硬币浮雕',
    ar: 'عملة تمثال الحرية',
  },
  'turnyourfavoritephotointoembossedartworkwithlaserpeckerlp5': {
    en: 'Photo to embossed artwork',
    zh: '照片变为浮雕艺术品',
    ar: 'حول صورتك إلى عمل فني بارز',
  },
  '金属铝': {
    en: 'Metal · Aluminum',
    zh: '金属，铝',
    ar: 'معدن · ألمنيوم',
  },
  '铝': {
    en: 'Aluminum',
    zh: '铝',
    ar: 'ألمنيوم',
  },
}

export function videoTitleEn(v: { title: string; url: string }): string
export function videoTitleEn(base: string): string
export function videoTitleEn(v: { title: string; url: string } | string): string {
  const base = typeof v === 'string' ? v : basenameKey(v.url)
  return galleryVideoTitles[base]?.en
}

export function videoTitleZh(v: { title: string; url: string }): string
export function videoTitleZh(base: string): string
export function videoTitleZh(v: { title: string; url: string } | string): string {
  const base = typeof v === 'string' ? v : basenameKey(v.url)
  return galleryVideoTitles[base]?.zh
}

export function videoTitleAr(v: { title: string; url: string }): string
export function videoTitleAr(base: string): string
export function videoTitleAr(v: { title: string; url: string } | string): string {
  const base = typeof v === 'string' ? v : basenameKey(v.url)
  return galleryVideoTitles[base]?.ar
}

/**
 * 从视频 URL 提取「唯一 basename」规范化键。
 * 例：`.../%E9%92%A2.mp4` → `铝`
 *     `.../Personalize_Shoes_with_LaserPecker_LP5.mp4` → `personalizeshoeswithlaserpeckerlp5`
 * 规则与生成表时完全一致：去扩展名 → 去非字母/数字/汉字 → 小写。
 */
export function basenameKey(url: string): string {
  const name = decodeURIComponent(url.split('/').pop() ?? '')
    .replace(/\.(mp4|mov|webm|m4v)$/i, '')
  return name.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')
}