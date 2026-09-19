import { useRouteError } from 'react-router-dom'

import { ErrorFallback } from './AppErrorBoundary'

/**
 * React Router 路由级 errorElement。
 *
 * data router（createBrowserRouter）内部的错误边界会先于外层 AppErrorBoundary
 * 捕获路由渲染错误，若不指定 errorElement 就会渲染 React Router 自带的
 * "Unexpected Application Error!" 调试页。这里改为渲染品牌化的错误页。
 *
 * 懒加载 chunk 失败（部署后旧 chunk 404）已由 lazyWithReload 自动刷新处理，
 * 走到这里的是刷新后仍失败或非 chunk 类的渲染错误。
 */
function RouteErrorElement() {
  const error = useRouteError()
  console.error('Route error', error)

  return <ErrorFallback onReset={() => window.location.reload()} />
}

export default RouteErrorElement
