import styled from 'styled-components'
import { Ink } from '../../editorial'

/**
 * 落地页视频基础组件 —— 实拍场景视频统一走 public/videos/laserpeck/（同源静态资源，
 * 符合 CSP default-src 'self' 约束，禁止外链）。
 * 该目录是「应用场景」视频的唯一副本（原 public/videos/laser 的改名副本已删除），
 * 下方每个 key 均指向该目录中的原件（原先的 16 个改名文件与其字节完全一致）。
 * 自动播放（静音 + 循环 + playsInline），object-fit: cover 保证任何视口不变形，
 * preload="metadata" 控制首屏外流量开销。
 */
const VP = '/videos/laserpeck'
/** 逐段编码，与 gen-scenario-manifest.cjs 生成的 URL 规则保持一致 */
const v = (p: string) => `${VP}/${p.split('/').map(encodeURIComponent).join('/')}`

export const LASER_VIDEOS = {
  hero: v('分类1：雕刻材料/多场景应用.mp4'),
  wood: v('分类2：使用场景/礼品定制/Laser_Engraved_Football_Field_Snack_Board_with_LaserPecker_LX2.mp4'),
  metal: v('分类2：使用场景/logo刻印/金属，铝.mp4'),
  glass: v('分类2：使用场景/杯子改造/Customized_Coffee_Jar_with_LaserPecker_LP5.mp4'),
  leather: v('分类2：使用场景/礼品定制/The_best_gift_says_we_thought_of_you._Engraved_by_LP4._backtoschool_laserpecker_giftideas.mp4'),
  fabric: v('分类2：使用场景/衣服、饰品定制/Create_One-of-a-Kind_Clothes_with_LaserPecker_LP4.mp4'),
  plastic: v('分类2：使用场景/3D刻印/Fast_engraving_on_the_switch_with_LaserPecker_LP2.mp4'),
  stone: v('分类2：使用场景/3D刻印/Stone_3D_Embossing_with_LaserPecker_LP5 (1).mp4'),
  coin3d: v('分类2：使用场景/3D刻印/3D_Embossing_a_Brass_Coin_with_the_LaserPecker_LP5.mp4'),
  colorLogo: v('分类2：使用场景/logo刻印/Color_Engraving_with_LaserPecker_LP4.mp4'),
  tumbler: v('分类2：使用场景/杯子改造/LaserPecker_2_-_custom_engraved_Tumbler._DiY_engraving_full_review_coming_soon.mp4'),
  gift: v('分类2：使用场景/礼品定制/Laserpecker_2_lasercut_laserengraving_lasermachine_leathercraft_onsitesouvenir_smallbusiness.mp4'),
  buttons: v('分类2：使用场景/衣服、饰品定制/Deep-engraved_Buttons_with_LaserPecker_LP5.mp4'),
  shoes: v('分类2：使用场景/鞋类刻印/Personalize_Shoes_with_LaserPecker_LP5.mp4'),
  lp1: v('分类2：使用场景/logo刻印/LaserPecker_LP1_Plus_in_Action_Fully_Upgraded_Still_Portable.mp4'),
  rotary: v('分类2：使用场景/杯子改造/Glass_engraving_with_LaserPecker_LP4_and_rotary_tool.mp4'),
} as const

const VideoEl = styled.video<{ $ratio?: string }>`
  display: block;
  width: 100%;
  aspect-ratio: ${p => p.$ratio ?? '3 / 4'};
  object-fit: cover;
  background: ${Ink.sunken};
  border-radius: inherit;
`

export default function LaserVideo({
  src,
  ratio = '3 / 4',
  className,
}: {
  src: string
  /** 竖版默认 3/4，横版场景可传 '16 / 9' 等 */
  ratio?: string
  className?: string
}) {
  return (
    <VideoEl
      $ratio={ratio}
      className={className}
      src={src}
      autoPlay
      muted
      loop
      playsInline
      preload="metadata"
      aria-hidden="true"
    />
  )
}
