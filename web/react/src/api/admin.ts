import { get, post, put, del, patch, postWithProgress, ensureCSRFCookie } from './request';

// ==================== Types ====================

export interface LoginResult { authenticated: boolean; }

export interface AdminUser {
  id: number;
  username: string;
  is_superuser: boolean;
  is_group_leader: boolean;
  group_name?: string;
  group_id?: number;
}

export interface SPUItem {
  id: number;
  name: string;
  brand_name: string;
  category_path: string;
  main_image: string;
  status: string;
  status_display: string;
  price_range: { min: string; max: string } | null;
  sku_count: number;
  specs?: { name: string; values: string[] }[];
  created_at: string;
}

export interface SPUFormData {
  name: string;
  brand_id: number;
  category_id: number;
  main_image?: string;
  description?: string;
  /** 创建时初始状态：draft（保存）/ on_sale（保存并上架）。仅超管创建时生效。 */
  status?: 'draft' | 'on_sale';
  /** 多语言商品名称/描述（英文 / 阿拉伯语） */
  name_en?: string;
  description_en?: string;
  name_ar?: string;
  description_ar?: string;
  specs?: { name: string; values: string[] }[];
  /** 显式 SKU 列表：创建时随请求提交，后端据此创建 SKU 并跳过 specs 自动生成 */
  skus?: {
    spec_values: Record<string, string>;
    price: string | number;
    stock: number;
    discount_price?: string | number | null;
    shelf_status?: string;
    /** SKU 名称（历史字段名 sku_code 亦兼容） */
    sku_name?: string;
    sku_code?: string;
    barcode?: string;
    weight?: string;
    track_inventory?: boolean;
  }[];
}

export interface SKUItem {
  id: number;
  spec_values: Record<string, string>;
  price: number;
  discount_price: number | null;
  stock: number;
  shelf_status: string;
  sku_name: string;
  /** 兼容别名：旧接口仍返回 sku_code */
  sku_code?: string;
  barcode: string;
  weight: string;
  track_inventory: boolean;
  spu_name?: string;
  spu_id?: number;
}

export interface CategoryNode {
  id: number;
  name: string;
  parent_id: number | null;
  level: number;
  is_active: boolean;
  children: CategoryNode[];
  /** 分类类型：product=普通商品 / showcase=作品展示（非商品） */
  kind?: 'product' | 'showcase';
}

export interface BrandItem {
  id: number;
  name: string;
  logo_url: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface TagItem {
  id: number;
  name: string;
  /** 2.1 话题式标签：product=产品标签 / activity=活动标签 */
  tag_type?: 'product' | 'activity';
  color: string;
  is_active: boolean;
  created_at: string;
}

/** 已保存的媒体项（后端 ProductMedia 返回） */
export interface ProductMediaItem {
  id: number;
  media_type: 'image' | 'video';
  sort_order: number;
  status: 'pending' | 'active' | 'rejected';
  alt_text: string;
  file_size: number;
  thumb_url?: string;
  list_url?: string;
  large_url?: string;
  original_url?: string;
  video_url?: string;
  video_thumb_url?: string;
  video_list_url?: string;
  video_large_url?: string;
  created_at?: string;
}

/** 管理端 SPU 详情完整类型（含 product_kind / media / tags[].color） */
export interface SPUAdminDetail {
  id: number;
  name: string;
  brand_id: number;
  brand_name: string;
  category_id: number;
  category_path: string;
  description: string;
  name_en?: string;
  description_en?: string;
  name_ar?: string;
  description_ar?: string;
  main_image: string;
  specs: { name: string; values: string[] }[];
  status: string;
  status_display: string;
  submitted_by?: string | null;
  submitted_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_comment?: string;
  scheduled_publish_at?: string | null;
  scheduled_unpublish_at?: string | null;
  skus: SKUItem[];
  tags: TagItem[];
  media: ProductMediaItem[];
  product_kind: 'physical' | 'virtual';
  created_at: string;
  updated_at: string;
}

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface OperationLogItem {
  id: number;
  action: string;
  resource_type: string;
  resource_id: number;
  changes: Record<string, unknown>;
  ip_address: string;
  user: string;
  created_at: string;
}

export interface ApplicationItem {
  id: number;
  type: string;
  type_label: string;
  status: string;
  applicant_name: string;
  created_at: string;
  reviewed_at: string | null;
  review_comment: string | null;
  detail: Record<string, unknown>;
}

export interface CouponItem {
  id: number;
  code: string;
  discount_type: 'fixed' | 'percent';
  amount: number;
  min_amount: number;
  max_discount: number | null;
  stackable: boolean;
  start_time: string;
  end_time: string;
  total_count: number;
  per_user_limit: number;
  claimed_count: number;
  used_count: number;
  created_at: string;
}

// Compatibility aliases used by AdminCoupons.tsx
export type Coupon = CouponItem;

/** 专属推广码（引流追踪）：同一张基础券可挂多个推广码 */
export interface PromoCodeItem {
  id: number;
  coupon: number;
  coupon_code: string;
  code: string;
  name: string;
  note: string;
  is_active: boolean;
  claim_count: number;
  paid_order_count: number;
  gmv: number | string;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  /** 看板聚合：独立领取用户数 */
  unique_users?: number;
}

export interface PromoCodeCreateData {
  codes?: string[];
  count?: number;
  prefix?: string;
  name?: string;
  note?: string;
}

export interface CouponFormData {
  code?: string;
  discount_type: 'fixed' | 'percent';
  amount: number;
  min_amount: number;
  max_discount?: number | null;
  stackable: boolean;
  is_active?: boolean;
  total_count: number;
  per_user_limit: number;
  start_time: string;
  end_time: string;
}

export interface AuditLogItem {
  id: number;
  user: string | null;
  user_id: number | null;
  action: string;
  resource_type: string;
  resource_id: number;
  changes: Record<string, unknown>;
  extra_data?: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface TaskItem {
  task_id: string;
  type: string;
  state: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILURE';
  current: number;
  total: number;
  error_message?: string;
  created_at: string;
}

export interface RecycleItem {
  id: number;
  name: string;
  brand_name: string;
  category_name: string;
  sku_count: number;
  deleted_at: string;
}

export interface PaginatedData<T> {
  /** DRF 标准分页字段 */
  results?: T[];
  /** SPU 列表使用 items 字段 */
  items?: T[];
  /** 后端返回的计数字段 (count 或 total) */
  count?: number;
  total: number;
  page: number;
  /** page_size 或 size */
  page_size?: number;
  size?: number;
}

// ==================== API ====================

export const adminAPI = {
  // Auth
  login: async (username: string, password: string) => {
    await ensureCSRFCookie();
    return post<LoginResult>('/users/login/', {
      username,
      password,
    });
  },
  logout: () => post('/users/session/logout/', {}),

  // SPU
  getSPUs: (params?: Record<string, unknown>) =>
    get<PaginatedData<SPUItem>>('/goods/spu/admin', params),
  getSPU: (id: number) =>
    get<SPUAdminDetail>(`/goods/spu/${id}/admin`),
  createSPU: (data: SPUFormData) =>
    post<SPUItem>('/goods/spu/create', data),
  createSPUWithMedia: (formData: FormData) =>
    post<SPUItem>('/goods/spu/create', formData),
  updateSPU: (id: number, data: Partial<SPUFormData>) =>
    put<SPUItem>(`/goods/spu/${id}/update`, data),
  /** 商品内容翻译（腾讯云机器翻译），返回翻译后的文本 */
  translateText: (data: { text: string; source?: string; target?: string }) =>
    post<{ translated_text: string }>('/goods/spu/translate', data),
  deleteSPU: (id: number) =>
    del(`/goods/spu/${id}/delete`),
  shelfSPU: (id: number, data: { action: string }) =>
    post(`/goods/spu/${id}/shelf`, data),
  scheduleSPU: (id: number, data: { publish_at?: string; unpublish_at?: string }) =>
    post(`/goods/spu/${id}/schedule`, data),
  duplicateSPU: (id: number) =>
    post(`/goods/spu/${id}/duplicate`, {}),

  // Batch
  batchSPU: (data: { action: string; spu_ids: number[]; data?: Record<string, unknown> }) =>
    post<{ task_id: string }>('/goods/spu/batch', data),
  getBatchProgress: (taskId: string) =>
    get<{ task_id: string; state: string; current: number; total: number }>(`/goods/spu/batch/task/${taskId}`),

  // SKU
  getSKUs: (spuId: number) =>
    get<SKUItem[]>(`/goods/sku/admin?spu_id=${spuId}`),
  searchSKUs: (q: string) =>
    get<{ items: (SKUItem & { spu_name: string; spu_id: number })[] }>(`/goods/sku/search?q=${encodeURIComponent(q)}&limit=20`),
  batchCreateSKU: (data: Record<string, unknown>) =>
    post<SKUItem[]>('/goods/sku/batch', data),
  updateSKU: (id: number, data: Record<string, unknown>) =>
    put<SKUItem>(`/goods/sku/${id}/update`, data),
  deleteSKU: (id: number) =>
    del(`/goods/sku/${id}/delete`),

  // Category
  getCategoryTree: () =>
    get<CategoryNode[]>('/goods/category/tree'),
  getCategorySubtree: () =>
    get<CategoryNode[]>('/goods/category/subtree'),
  createCategory: (data: { name: string; parent_id: number | null; level: number; admin_group_id?: number; kind?: 'product' | 'showcase' }) =>
    post<CategoryNode>('/goods/category/create', data),
  updateCategory: (id: number, data: Record<string, unknown>) =>
    put<CategoryNode>(`/goods/category/${id}/update`, data),
  deleteCategory: (id: number) =>
    del(`/goods/category/${id}/delete`),
  migrateCategory: (data: { from_category_id: number; to_category_id: number }) =>
    post<{ migrated_count: number }>('/goods/category/migrate', data),

  // Brand
  getBrands: () =>
    get<BrandItem[]>('/goods/brand'),
  createBrand: (data: { name: string; logo_url?: string; description?: string; is_active?: boolean }) =>
    post<BrandItem>('/goods/brand/create', data),
  updateBrand: (id: number, data: Partial<BrandItem>) =>
    put<BrandItem>(`/goods/brand/${id}/update`, data),
  deleteBrand: (id: number) =>
    del(`/goods/brand/${id}/delete`),

  // Tag
  getTags: () =>
    get<TagItem[]>('/goods/tag'),
  createTag: (data: { name: string; tag_type?: 'product' | 'activity'; color?: string; is_active?: boolean }) =>
    post<TagItem>('/goods/tag/create', data),
  updateTag: (id: number, data: Partial<TagItem>) =>
    put<TagItem>(`/goods/tag/${id}/update`, data),
  deleteTag: (id: number) =>
    del(`/goods/tag/${id}/delete`),
  setSPUTags: (data: { spu_id: number; tag_ids: number[] }) =>
    post('/goods/spu_tag', data),
  removeSPUTag: (data: { spu_id: number; tag_ids: number[] }) =>
    del('/goods/spu_tag/remove', data),

  // Media
  /** 获取 SPU 的媒体列表（含 alt_text） */
  getMediaBySPU: (spuId: number) =>
    get<ProductMediaItem[]>(`/goods/media/spu/${spuId}`),
  /** 更新媒体信息（alt_text / sort_order） */
  updateMedia: (mediaId: number, data: { alt_text?: string; sort_order?: number }) =>
    patch<{ id: number; alt_text: string; sort_order: number; message: string }>(
      `/goods/media/${mediaId}/update`, data,
    ),
  /** 删除媒体 */
  deleteMedia: (mediaId: number) =>
    del<{ detail: string }>(`/goods/media/${mediaId}/delete`),
  /** 编辑模式：向已有 SPU 上传图片（四尺寸 FormData，XHR 进度） */
  uploadMedia: (
    spuId: number,
    formData: FormData,
    onProgress?: (percent: number) => void,
  ) =>
    postWithProgress<ProductMediaItem>(
      `/goods/media/spu/${spuId}/upload`, formData, onProgress,
    ),
  /** 原地重新裁剪/替换单张图片（不新增记录；四尺寸 FormData，XHR 进度） */
  replaceMedia: (
    mediaId: number,
    formData: FormData,
    onProgress?: (percent: number) => void,
  ) =>
    postWithProgress<ProductMediaItem>(
      `/goods/media/${mediaId}/replace`, formData, onProgress,
    ),
  /** 1.2 视频上传（编辑模式）：单文件 video/mp4|webm|mov，≤200MB
   *  thumbFile 可选：视频首帧图（WebP），后端存入 video_thumb_url 作为列表缩略图。 */
  uploadVideo: (
    spuId: number,
    file: File,
    onProgress?: (percent: number) => void,
    thumbFile?: Blob | null,
  ) => {
    const fd = new FormData();
    fd.append('file', file);
    if (thumbFile) {
      fd.append('thumb', thumbFile, 'frame.webp');
    }
    return postWithProgress<ProductMediaItem>(
      `/goods/media/spu/${spuId}/video/upload`, fd, onProgress,
    );
  },

  /** 1.3 视频分片直传：绕开 Cloudflare 100MB 边缘限制。
   *  流程：chunk-init 申请 R2 multipart → 按 8MB 分片逐块经 api 上传（每片远小于
   *  CF 限制）→ chunk-complete 合并并新建 ProductMedia。无需配置 bucket CORS。 */
  async uploadVideoDirect(
    spuId: number,
    file: File,
    onProgress?: (percent: number) => void,
    thumbFile?: Blob | null,
  ): Promise<ProductMediaItem> {
    const content_type = file.type || 'video/mp4'
    const file_size = file.size

    // ① 申请分片上传
    const init = await post<{
      key: string;
      upload_id: string;
      chunk_size: number;
      chunks: number;
    }>(`/goods/media/spu/${spuId}/video/chunk-init`, {
      file_name: file.name,
      content_type,
      file_size,
    })
    const { key, upload_id, chunk_size } = init
    // 自适应分片：某一片超时时把该片切成一半重传（慢网络 8MB 未能在 600s 内传完时兜底），
    // 每次减半，最低降到 1MB。R2 要求除最后一片外每片 ≥5MB —— 但减半仅发生在上传中途
    // 的超时重试（此时该片并未上到 R2，只是浏览器端超时），合并时该部分用最终成功的小片。
    // 注意：所有最终上传的片（除最后一片）会经 chunk-complete 交给 R2，必须满足 ≥5MB，
    // 因此减半下限设为 5MB；1 片 8MB→4MB 不再允许，若仍超时直接报错由用户处理网络。
    const parts: { part_number: number; etag: string }[] = []
    const MIN_CHUNK = 5 * 1024 * 1024

    // ② 逐块上传；timeout/网络错误时当前块减半递归重传，避免慢网整批失败
    let partNumber = 1
    let offset = 0
    let curChunk = chunk_size
    while (offset < file_size) {
      const sliceEnd = Math.min(offset + curChunk, file_size)
      const blob = file.slice(offset, sliceEnd)
      const fd = new FormData()
      fd.append('upload_id', upload_id)
      fd.append('key', key)
      fd.append('part_number', String(partNumber))
      fd.append('part', blob, 'chunk.bin')
      try {
        const res = await postWithProgress<{ etag: string }>(
          `/goods/media/spu/${spuId}/video/chunk-upload`, fd,
        )
        parts.push({ part_number: partNumber, etag: res.etag })
        offset = sliceEnd
        partNumber += 1
        // 成功后按需恢复分片大小（避免整批被网络探测压低）
        if (curChunk < chunk_size) curChunk = chunk_size
        if (onProgress) {
          onProgress(Math.round((offset / file_size) * 100))
        }
      } catch (e) {
        // 超时/网络错误：分片减半重试（≥5MB），保持同一 part_number 覆盖该片
        if (curChunk > MIN_CHUNK) {
          curChunk = Math.floor(curChunk / 2)
          // 压缩到完整 5MB 以上（对齐 MIN_CHUNK 下限）
          if (curChunk < MIN_CHUNK) curChunk = MIN_CHUNK
          if (onProgress) onProgress(Math.round((offset / file_size) * 100))
        } else {
          throw e
        }
      }
    }

    // ③ 合并并建立记录
    const completeFd = new FormData()
    completeFd.append('key', key)
    completeFd.append('upload_id', upload_id)
    completeFd.append('content_type', content_type)
    completeFd.append('file_size', String(file_size))
    completeFd.append('parts', JSON.stringify(parts))
    if (thumbFile) {
      completeFd.append('thumb', thumbFile, 'frame.webp')
    }
    return postWithProgress<ProductMediaItem>(
      `/goods/media/spu/${spuId}/video/chunk-complete`, completeFd,
    );
  },

  // Notification（统一走通用通知中心 /notification/，含客服消息 cs_* 通知）
  getNotifications: (params?: { page?: number; per_page?: number }) =>
    get<PaginatedData<NotificationItem>>('/notification/', params),
  getUnreadCount: () =>
    get<{ unread_count: number }>('/notification/unread_count/'),
  markRead: (id: number) =>
    post(`/notification/${id}/read/`, {}),
  markAllRead: () =>
    post('/notification/read-all/', {}),

  // Stats
  getAdminStats: () =>
    get<Record<string, unknown>>('/goods/stats'),

  // Recycle
  getRecycleList: () =>
    get<RecycleItem[]>('/goods/recycle'),
  restoreSPU: (id: number) =>
    post(`/goods/recycle/${id}/restore`, {}),
  permanentDeleteSPU: (id: number) =>
    del(`/goods/recycle/${id}/permanent`),

  // Coupon
  getCoupons: (params?: { page?: number; search?: string }) =>
    get<PaginatedData<CouponItem>>('/promotion/coupon', params),
  createCoupon: (data: Record<string, unknown>) =>
    post<CouponItem>('/promotion/coupon/create', data),
  updateCoupon: (id: number, data: Record<string, unknown>) =>
    put<CouponItem>(`/promotion/coupon/${id}/update`, data),
  deleteCoupon: (id: number) =>
    del(`/promotion/coupon/${id}/delete`),
  setCouponScope: (id: number, data: { scope_type: string; target_ids: number[] }) =>
    post(`/promotion/coupon/${id}/scope`, data),

  // Promo Code（专属券推广码 / 引流追踪）
  getPromoCodes: (couponId: number) =>
    get<PromoCodeItem[]>(`/promotion/coupon/${couponId}/promo-codes`),
  createPromoCodes: (couponId: number, data: PromoCodeCreateData) =>
    post<PromoCodeItem[]>(`/promotion/coupon/${couponId}/promo-codes`, data),
  getPromoDashboard: (couponId: number) =>
    get<PromoCodeItem[]>(`/promotion/coupon/${couponId}/promo-dashboard`),
  // 单码更新（启用/停用、改名改备注）
  updatePromoCode: (id: number, data: Partial<Pick<PromoCodeItem, 'is_active' | 'name' | 'note'>>) =>
    patch<PromoCodeItem>(`/promotion/coupon/promo/${id}/`, data),
  // 单码删除
  deletePromoCode: (id: number) =>
    del<{ message: string }>(`/promotion/coupon/promo/${id}/`),

  // Email Templates
  getEmailTemplates: () =>
    get<{ code: number; data: EmailTemplateItem[] }>('/users/email/templates/'),
  updateEmailTemplate: (templateType: string, data: { subject: string; html_body: string; text_body: string; is_active: boolean }) =>
    post(`/users/email/templates/${templateType}/`, data),
  resetEmailTemplate: (templateType: string) =>
    post(`/users/email/templates/${templateType}/reset/`),

  // RBAC — 角色 × 权限矩阵 + 用户角色（管理面 /api/admin/users/，按 account_no 指认）
  getRbacMatrix: () =>
    get<RbacMatrix>('/rbac/matrix'),
  updateRbacRole: (role: string, permCodes: string[]) =>
    put<{ role: string; perm_codes: string[] }>('/rbac/matrix', { role, perm_codes: permCodes }),
  getRbacUsers: (params?: { role?: string; account_no?: string; page?: number; size?: number }) =>
    get<PaginatedData<RbacUser>>('/admin/users/', params),
  updateUserRoles: (accountNo: string, roles: string[]) =>
    put<{ roles: string[] }>(`/admin/users/${accountNo}/roles`, { roles }),
};

export interface EmailTemplateItem {
  template_type: string;
  subject: string;
  html_body: string;
  text_body: string;
  is_active: boolean;
  updated_at: string | null;
}

export interface RbacRole {
  value: string;
  label: string;
}

export interface RbacPermission {
  code: string;
  label: string;
}

export interface RbacDomain {
  domain: string;
  permissions: RbacPermission[];
}

export interface RbacMatrix {
  roles: RbacRole[];
  domains: RbacDomain[];
  grants: Record<string, string[]>;
  superadmin_implicit: boolean;
  orphaned: string[];
}

export interface RbacUser {
  account_no: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
}

export default adminAPI;
