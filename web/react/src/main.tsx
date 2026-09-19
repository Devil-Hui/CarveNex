import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './assets/global.css'
import App from './App'

// 构建标记：用于确认部署是否更新到最新提交（可在浏览器控制台查看）
console.info('[CarveNex] build cnex-probe-src-20260919')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
