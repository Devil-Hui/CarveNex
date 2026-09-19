import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './assets/global.css'
import App from './App'
import { installChunkReloadHandler } from './utils/chunkReload'

// 部署后旧 chunk 404（Failed to fetch dynamically imported module）时自动刷新一次，
// 必须在渲染前注册，保证模块预加载失败也能被接住。
installChunkReloadHandler()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
