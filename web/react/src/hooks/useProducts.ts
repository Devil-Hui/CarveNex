/**
 * 从后端 API 获取商品数据，与 admin 后台操作保持一致。
 * 所有数据来自真实 API，不再使用 mock 降级。
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { publicAPI, type PublicSPU, type PublicCategory, type PromoTag } from '../api/public';
import { resolveMediaUrl } from '../api/chat';
import { PAGE_SIZE } from '../config';

// ── 类型 ──────────────────────────────────────────────────────

export interface Product {
  id: number;
  name: string;
  /** 多语言名称（英文 / 阿拉伯语） */
  name_en?: string;
  name_ar?: string;
  price: number;
  image: string;
  category: string;
  categoryId?: number;
  description: string;
  rating: number;
  reviews: number;
  badge?: string;
  originalPrice?: number;
  promo_tags?: PromoTag[];
}

export interface CategoryItem {
  id: number;
  name: string;
  icon: string;
  level: number;
  children?: CategoryItem[];
}

// ── 数据映射 ──────────────────────────────────────────────────

function mapSPUToProduct(spu: PublicSPU): Product {
  return {
    id: spu.id,
    name: spu.name,
    name_en: spu.name_en,
    name_ar: spu.name_ar,
    price: parseFloat(spu.min_price || '0') || 0,
    image: resolveMediaUrl(spu.main_image) || spu.main_image || '',
    category: spu.category_name || '',
    description: spu.description || '',
    rating: 0,
    reviews: 0,
    promo_tags: spu.promo_tags || [],
  };
}

// ── Hook: 商品列表 ────────────────────────────────────────────

export function useProducts(page = 1, per_page = 20, categoryId?: number, query = '', priceMin?: number, priceMax?: number) {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  const hasPriceFilter = (priceMin ?? null) !== null || (priceMax ?? null) !== null;

  const fetchProducts = useCallback(async () => {
    abortRef.current = false;
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { page, per_page };
      if (categoryId) params.category_id = categoryId;
      const response = query || hasPriceFilter
        ? await publicAPI.search({
            q: query || undefined,
            category_id: categoryId,
            price_min: priceMin ?? undefined,
            price_max: priceMax ?? undefined,
            page,
            per_page,
          })
        : await publicAPI.getSPUList(params);
      if (abortRef.current) return;
      const items = response.items || response.results || [];
      setProducts(items.map(mapSPUToProduct));
      setTotal(response.total || 0);
    } catch (err: any) {
      if (!abortRef.current) setError(err?.message || 'Failed to load products');
    } finally {
      if (!abortRef.current) setLoading(false);
    }
  }, [page, per_page, categoryId, query, priceMin, priceMax, hasPriceFilter]);

  useEffect(() => {
    fetchProducts();
    return () => { abortRef.current = true; };
  }, [fetchProducts]);

  return { products, total, loading, error, refetch: fetchProducts };
}

// ── Hook: 商品列表（无限下滑：翻页时累积，筛选变化时重置）────────

/**
 * 无限下滑版商品列表。
 * 与 useProducts 的区别：翻页时把新数据追加到已有列表尾部（而非整页替换），
 * 分类 / 搜索词 / 价格区间变化时自动重置回第 1 页。
 */
export function useProductsInfinite(
  per_page = PAGE_SIZE,
  categoryId?: number,
  query = '',
  priceMin?: number,
  priceMax?: number,
) {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 请求代次：筛选条件变化后，丢弃仍在飞行的旧请求结果，避免串页
  const reqGen = useRef(0);
  const pageRef = useRef(1);
  const busyRef = useRef(false);
  const hasMoreRef = useRef(false);

  const hasPriceFilter = (priceMin ?? null) !== null || (priceMax ?? null) !== null;

  /** 拉取指定页，返回已映射的商品与总数 */
  const fetchPage = useCallback(async (targetPage: number) => {
    const params: Record<string, unknown> = { page: targetPage, per_page };
    if (categoryId) params.category_id = categoryId;
    const response = query || hasPriceFilter
      ? await publicAPI.search({
          q: query || undefined,
          category_id: categoryId,
          price_min: priceMin ?? undefined,
          price_max: priceMax ?? undefined,
          page: targetPage,
          per_page,
        })
      : await publicAPI.getSPUList(params);
    const items = response.items || response.results || [];
    return { items: items.map(mapSPUToProduct), total: response.total || 0 };
  }, [per_page, categoryId, query, priceMin, priceMax, hasPriceFilter]);

  const hasMore = products.length < total;

  useEffect(() => { pageRef.current = page; }, [page]);
  useEffect(() => { hasMoreRef.current = hasMore; }, [hasMore]);

  // 筛选条件变化 → 回到第 1 页并整表替换
  const filterKey = `${categoryId ?? ''}|${query}|${priceMin ?? ''}|${priceMax ?? ''}`;
  useEffect(() => {
    const gen = ++reqGen.current;
    busyRef.current = false;
    setLoading(true);
    // 关键：筛选切换时若上一页请求仍在飞行，必须清掉 loadingMore，
    // 否则它会永久停在 true，导致后续「加载更多」被 loading 守卫挡死。
    setLoadingMore(false);
    setError(null);
    fetchPage(1)
      .then(({ items, total: t }) => {
        if (reqGen.current !== gen) return;
        setProducts(items);
        setTotal(t);
        setPage(1);
        pageRef.current = 1;
      })
      .catch((err: any) => {
        if (reqGen.current !== gen) return;
        setError(err?.message || 'Failed to load products');
      })
      .finally(() => {
        if (reqGen.current === gen) setLoading(false);
      });
  }, [filterKey, fetchPage]);

  /** 加载下一页并追加到列表尾部（按 id 去重，防止分页漂移出现重复卡片） */
  const loadMore = useCallback(async () => {
    if (busyRef.current || !hasMoreRef.current) return;
    const gen = reqGen.current;
    busyRef.current = true;
    setLoadingMore(true);
    const nextPage = pageRef.current + 1;
    try {
      const { items, total: t } = await fetchPage(nextPage);
      if (reqGen.current !== gen) return;
      setProducts((prev) => {
        const seen = new Set(prev.map((p) => p.id));
        return [...prev, ...items.filter((p) => !seen.has(p.id))];
      });
      setTotal(t);
      setPage(nextPage);
      pageRef.current = nextPage;
    } catch (err: any) {
      if (reqGen.current === gen) setError(err?.message || 'Failed to load products');
    } finally {
      // 无论成功/失败/被筛选切换作废，都必须释放忙碌锁与 loadingMore，
      // 否则哨兵会因 loading 一直为 true 而再也不触发加载。
      busyRef.current = false;
      setLoadingMore(false);
    }
  }, [fetchPage]);

  return { products, total, page, loading, loadingMore, hasMore, error, loadMore };
}

// ── Hook: 商品详情 ────────────────────────────────────────────

export function useProductDetail(spuId: number) {
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  useEffect(() => {
    if (!spuId) return;
    abortRef.current = false;
    setLoading(true);
    setError(null);
    publicAPI.getSPUDetail(spuId)
      .then((detail) => {
        if (abortRef.current) return;
        if (detail) {
          const minPrice = detail.skus?.length
            ? Math.min(...detail.skus.map(s => parseFloat(s.price || '0') || 0))
            : 0;
          setProduct({
            id: detail.id,
            name: detail.name,
            name_en: detail.name_en,
            name_ar: detail.name_ar,
            price: minPrice,
            image: resolveMediaUrl(detail.main_image) || detail.main_image || detail.skus?.[0]?.image_url || '',
            category: detail.category_path || '',
            categoryId: detail.category_id,
            description: detail.description || '',
            rating: 0,
            reviews: 0,
            promo_tags: detail.promo_tags || [],
          });
        }
      })
      .catch((err: any) => {
        if (!abortRef.current) setError(err?.message || 'Failed to load product');
      })
      .finally(() => { if (!abortRef.current) setLoading(false); });
    return () => { abortRef.current = true; };
  }, [spuId]);

  return { product, loading, error };
}

// ── Hook: 分类列表（树形） ────────────────────────────────────

export function useCategories() {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  useEffect(() => {
    const mapNode = (node: PublicCategory): CategoryItem => ({
      id: node.id,
      name: node.name,
      icon: '',
      level: node.level,
      children: node.children?.map(mapNode) || [],
    });
    abortRef.current = false;
    publicAPI.getCategoryTree()
      .then((tree) => {
        if (abortRef.current) return;
        if (Array.isArray(tree) && tree.length > 0) {
          setCategories(tree.map(mapNode));
        }
      })
      .catch((err: any) => {
        if (!abortRef.current) setError(err?.message || 'Failed to load categories');
      })
      .finally(() => { if (!abortRef.current) setLoading(false); });
    return () => { abortRef.current = true; };
  }, []);

  return { categories, loading, error };
}

// ── Hook: 扁平分类列表 ────────────────────────────────────────

export function useFlatCategories() {
  const [categories, setCategories] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef(false);

  useEffect(() => {
    abortRef.current = false;
    publicAPI.getCategoryTree()
      .then((tree) => {
        if (abortRef.current) return;
        const flat: { id: number; name: string }[] = [];
        const walk = (nodes: PublicCategory[]) => {
          for (const node of nodes) {
            flat.push({ id: node.id, name: node.name });
            if (node.children) walk(node.children);
          }
        };
        if (Array.isArray(tree)) walk(tree);
        setCategories(flat);
      })
      .catch(() => {})
      .finally(() => { if (!abortRef.current) setLoading(false); });
    return () => { abortRef.current = true; };
  }, []);

  return { categories, loading };
}
