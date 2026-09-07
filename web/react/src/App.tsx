import { createBrowserRouter, RouterProvider, Outlet, useLocation } from 'react-router-dom'
import { I18nProvider } from './i18n'
import { AppProvider } from './store/AppContext'
import { AdminAuthProvider } from './store/AdminAuthContext'
import GlobalLoading from './components/common/GlobalLoading'
import GlobalErrorToast from './components/common/GlobalErrorToast'
import MiniCartToast from './components/common/MiniCartToast'
import { CartProvider } from './store/CartContext'
import { UserProvider } from './store/UserContext'
import { CurrencyProvider } from './store/CurrencyContext'
import { routes } from './router'
import AppErrorBoundary from './components/common/AppErrorBoundary/AppErrorBoundary'
import ReauthModal from './components/common/ReauthModal'
import CustomerServiceFAB from './components/common/CustomerServiceFAB'

/**
 * 电商全局浮层（登录失效弹窗 / 客服悬浮球 / 加购提示）。
 * 落地页（/）为沉浸式品牌体验，不渲染这些电商界面元素。
 */
function CommerceOverlays() {
  const { pathname } = useLocation()
  if (pathname === '/') return null
  return (
    <>
      <ReauthModal />
      <CustomerServiceFAB />
      <MiniCartToast />
    </>
  )
}

/**
 * 根布局：渲染当前路由 + 电商浮层。
 * 使用 data router（createBrowserRouter）以支持 useBlocker 等
 * React Router v7 数据路由钩子（AdminProductForm 依赖它做未保存离开拦截）。
 */
function RootLayout() {
  return (
    <>
      <Outlet />
      <CommerceOverlays />
    </>
  )
}

// 无路径布局路由包裹全部业务路由，保证浮层在所有页面渲染
const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: routes,
  },
])

function App() {
  return (
    <I18nProvider>
    <AppErrorBoundary>
    <AppProvider>
      <GlobalLoading />
      <GlobalErrorToast />
      <CurrencyProvider>
      <UserProvider>
      <CartProvider>
        <AdminAuthProvider>
        <RouterProvider router={router} />
        </AdminAuthProvider>
      </CartProvider>
      </UserProvider>
      </CurrencyProvider>
    </AppProvider>
    </AppErrorBoundary>
    </I18nProvider>
  )
}

export default App
