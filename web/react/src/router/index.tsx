// 路由配置集中管理

import { Suspense } from 'react'
import { Navigate, type RouteObject } from 'react-router-dom'
import Home from '../pages/Home/Home'
// 懒加载路由统一走 lazyWithReload：部署后旧 chunk 404 时自动刷新，
// 而不是把 "Unexpected Application Error!" 抛给用户。
import { lazyWithReload } from '../utils/chunkReload'
const Category = lazyWithReload(() => import('../pages/Category/Category'))
const ProductDetail = lazyWithReload(() => import('../pages/ProductDetail/ProductDetail'))
const Cart = lazyWithReload(() => import('../pages/Cart/Cart'))
const Checkout = lazyWithReload(() => import('../pages/Checkout/Checkout'))
const PaymentReturn = lazyWithReload(() => import('../pages/PaymentReturn/PaymentReturn'))
const MockPayment = lazyWithReload(() => import('../pages/MockPayment/MockPayment'))
const Profile = lazyWithReload(() => import('../pages/Profile/Profile'))
const AuthPage = lazyWithReload(() => import('../pages/Auth/AuthPage'))
const SetPasswordPage = lazyWithReload(() => import('../pages/Auth/SetPasswordPage'))
const ForgotPasswordPage = lazyWithReload(() => import('../pages/Auth/ForgotPasswordPage'))
const CouponShare = lazyWithReload(() => import('../pages/CouponShare/CouponShare'))
const TrackOrder = lazyWithReload(() => import('../pages/TrackOrder/TrackOrder'))
const AboutPage = lazyWithReload(() => import('../pages/About/AboutPage'))
const Chat = lazyWithReload(() => import('../pages/Chat/Chat'))
const OrderDetail = lazyWithReload(() => import('../pages/OrderDetail/OrderDetail'))
const Notifications = lazyWithReload(() => import('../pages/Notifications/Notifications'))
const Favorites = lazyWithReload(() => import('../pages/Favorites/Favorites'))
const PromoShowcase = lazyWithReload(() => import('../pages/PromoShowcase/PromoShowcase'))
import { RoleProtectedRoute } from '../components/admin/ProtectedRoute'

// Admin pages — lazy loaded
const AdminLogin = lazyWithReload(() => import('../pages/Admin/AdminLogin'))
const AdminLayout = lazyWithReload(() => import('../pages/Admin/AdminLayout'))
const AdminDashboard = lazyWithReload(() => import('../pages/Admin/AdminDashboard'))
const AdminProducts = lazyWithReload(() => import('../pages/Admin/AdminProducts'))
const AdminProductForm = lazyWithReload(() => import('../pages/Admin/AdminProductForm'))

const AdminCategories = lazyWithReload(() => import('../pages/Admin/AdminCategories'))
const AdminBrands = lazyWithReload(() => import('../pages/Admin/AdminBrands'))
const AdminTags = lazyWithReload(() => import('../pages/Admin/AdminTags'))
const AdminNotifications = lazyWithReload(() => import('../pages/Admin/AdminNotifications'))
const AdminCoupons = lazyWithReload(() => import('../pages/Admin/AdminCoupons'))
const AdminRecycleBin = lazyWithReload(() => import('../pages/Admin/AdminRecycleBin'))
const AdminOrders = lazyWithReload(() => import('../pages/Admin/AdminOrders'))
const AdminChatList = lazyWithReload(() => import('../pages/Admin/AdminChatList'))
const AdminChatDetail = lazyWithReload(() => import('../pages/Admin/AdminChatDetail'))
const AdminEmailTemplates = lazyWithReload(() => import('../pages/Admin/AdminEmailTemplates'))
const AdminImport = lazyWithReload(() => import('../pages/Admin/AdminImport'))
const AdminMediaImport = lazyWithReload(() => import('../pages/Admin/AdminMediaImport'))
const AdminPromoCodes = lazyWithReload(() => import('../pages/Admin/AdminPromoCodes'))
const AdminAds = lazyWithReload(() => import('../pages/Admin/AdminAds'))

const PageLoading = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    fontSize: '14px',
    color: '#999',
  }}>
    Loading...
  </div>
)

export const routes: RouteObject[] = [
  // ── admin.carvenex.com → 自动跳转管理登录 ──
  {
    path: '/',
    element: typeof window !== 'undefined' && window.location.hostname === 'admin.carvenex.com'
      ? <Navigate to="/admin/login" replace />
      : <Home />,
  },
  { path: '/category', element: <Suspense fallback={<PageLoading />}><Category /></Suspense> },
  { path: '/product/:id', element: <Suspense fallback={<PageLoading />}><ProductDetail /></Suspense> },
  { path: '/cart', element: <Suspense fallback={<PageLoading />}><Cart /></Suspense> },
  { path: '/checkout', element: <Suspense fallback={<PageLoading />}><Checkout /></Suspense> },
  { path: '/payment/return', element: <Suspense fallback={<PageLoading />}><PaymentReturn /></Suspense> },
  { path: '/mock-payment/:paymentNo', element: <Suspense fallback={<PageLoading />}><MockPayment /></Suspense> },
  { path: '/profile', element: <Suspense fallback={<PageLoading />}><Profile /></Suspense> },
  { path: '/auth/set-password', element: <Suspense fallback={<PageLoading />}><SetPasswordPage /></Suspense> },
  { path: '/forgot-password', element: <Suspense fallback={<PageLoading />}><ForgotPasswordPage /></Suspense> },
  { path: '/auth', element: <Suspense fallback={<PageLoading />}><AuthPage /></Suspense> },
  { path: '/login', element: <Navigate to="/auth?tab=login" replace /> },
  { path: '/register', element: <Navigate to="/auth?tab=register" replace /> },
  { path: '/coupon/:code', element: <Suspense fallback={<PageLoading />}><CouponShare /></Suspense> },
  { path: '/coupon', element: <Navigate to="/profile?tab=coupons" replace /> },
  { path: '/about', element: <Suspense fallback={<PageLoading />}><AboutPage /></Suspense> },
  { path: '/chat', element: <Suspense fallback={<PageLoading />}><Chat /></Suspense> },
  { path: '/order/:order_no', element: <Suspense fallback={<PageLoading />}><OrderDetail /></Suspense> },
  { path: '/notifications', element: <Suspense fallback={<PageLoading />}><Notifications /></Suspense> },
  { path: '/favorites', element: <Suspense fallback={<PageLoading />}><Favorites /></Suspense> },
  { path: '/promo-precision', element: <Suspense fallback={<PageLoading />}><PromoShowcase /></Suspense> },
  { path: '/track', element: <Suspense fallback={<PageLoading />}><TrackOrder /></Suspense> },

  // ── Admin login (standalone, no layout) ──
  {
    path: '/admin/login',
    element: (
      <Suspense fallback={<PageLoading />}>
        <AdminLogin />
      </Suspense>
    ),
  },

  // ── Admin protected routes (wrapped in layout) ──
  {
    path: '/admin',
    element: (
      <Suspense fallback={<PageLoading />}>
        <RoleProtectedRoute>
          <AdminLayout />
        </RoleProtectedRoute>
      </Suspense>
    ),
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: 'dashboard', element: <Suspense fallback={<PageLoading />}><AdminDashboard /></Suspense> },
      { path: 'products', element: <Suspense fallback={<PageLoading />}><AdminProducts /></Suspense> },
      { path: 'ads', element: <Suspense fallback={<PageLoading />}><AdminAds /></Suspense> },
      { path: 'products/create', element: <Suspense fallback={<PageLoading />}><AdminProductForm /></Suspense> },
      { path: 'products/:id', element: <Suspense fallback={<PageLoading />}><AdminProductForm /></Suspense> },
      { path: 'import', element: <Suspense fallback={<PageLoading />}><AdminImport /></Suspense> },
      { path: 'media-import', element: <Suspense fallback={<PageLoading />}><AdminMediaImport /></Suspense> },
      { path: 'categories', element: <Suspense fallback={<PageLoading />}><AdminCategories /></Suspense> },
      { path: 'brands', element: <Suspense fallback={<PageLoading />}><AdminBrands /></Suspense> },
      { path: 'tags', element: <Suspense fallback={<PageLoading />}><AdminTags /></Suspense> },
      { path: 'notifications', element: <Suspense fallback={<PageLoading />}><AdminNotifications /></Suspense> },
      { path: 'coupons', element: <Suspense fallback={<PageLoading />}><AdminCoupons /></Suspense> },
      { path: 'coupons/promo/:couponId', element: <Suspense fallback={<PageLoading />}><AdminPromoCodes /></Suspense> },
      { path: 'orders', element: <Suspense fallback={<PageLoading />}><AdminOrders /></Suspense> },
      { path: 'recycle-bin', element: <Suspense fallback={<PageLoading />}><AdminRecycleBin /></Suspense> },
      { path: 'chat', element: <Suspense fallback={<PageLoading />}><AdminChatList /></Suspense> },
      { path: 'chat/:id', element: <Suspense fallback={<PageLoading />}><AdminChatDetail /></Suspense> },
      { path: 'email-templates', element: <Suspense fallback={<PageLoading />}><AdminEmailTemplates /></Suspense> },
      { path: '*', element: <Navigate to="/admin/products" replace /> },
    ],
  },
]
