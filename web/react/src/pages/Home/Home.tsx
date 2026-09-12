import styled from 'styled-components'
import { Ink, Font } from './editorial'
import PageLayout from '../../components/layout/PageLayout/PageLayout'
import Hero from './components/Hero'
import ScenarioGallery from './components/ScenarioGallery'
import UseCases from './components/UseCases'
import Journey from './components/Journey'
import Closing from './components/Closing'

/**
 * CarveNex — 激光雕刻機落地頁
 * ─────────────────────────────────────────────────────────
 * 敘事結構（認知 → 能力 → 場景 → 信任 → 轉化）：
 *   Hero        價值主張 + 實拍雕刻影片前置 + 社交證明
 *   Gallery     應用場景視頻畫廊（雙行無限滾動 + 聚焦 + 展開）
 *   UseCases    六大使用場景（3D 刻印 / Logo / 杯子 / 禮品 / 衣飾 / 鞋類）
 *   Journey     六步上手流程 + 實拍演示
 *   Closing     CTA 收尾
 */
const Page = styled.div`
  background: ${Ink.paper};
  font-family: ${Font.body};
  color: ${Ink.black};
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  h1,
  h2,
  h3 {
    text-wrap: balance;
  }

  p {
    text-wrap: pretty;
  }
`

export default function Home() {
  return (
    <PageLayout>
      <Page>
        <main>
          <Hero />
          <ScenarioGallery />
          <UseCases />
          <Journey />
          <Closing />
        </main>
      </Page>
    </PageLayout>
  )
}