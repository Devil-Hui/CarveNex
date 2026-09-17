"""
初始商品导入（幂等）—— 从单一数据源目录把「初始商品」落到数据库与媒体存储
=====================================================================
数据源约定（本命令读取构建进镜像的目录）：
    <backend>/seed_products/
        products.xlsx              # 商品信息表（与「产品资料/产品描述和价格1.xlsx」一致）
        images/<目录名>/           # 每个子目录 = 一个商品的原图（jpg/png/webp…）

本命令会：
  1) 确保品牌 LaserPecker 存在
  2) 确保英文分类树存在（Laser Engravers / Accessories / Materials & Blanks）
  3) 逐行读取 xlsx → 创建 SPU(ON_SALE) + SKU（原价/现价 → price/discount_price）
  4) 从 images/<目录名>/ 导入图片到 ProductMedia（复用后台转码 → 四尺寸 WebP）
  5) 幂等：已存在同名 SPU 则跳过（不重复建 SPU、不重复导媒体）。
     例外：若该 SPU 的媒体文件在磁盘上已缺失（如 media 卷被清空，而
     ProductMedia 记录仍在），会自动补回图片，避免「有商品无图」。

用法（在 setup.sh 的 init_system 中调用）：
    python manage.py seed_products --env=prod
    python manage.py seed_products --dry-run    # 预览：只扫描、不写入
"""

import os
import re
import zlib

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.goods.models import Brand, Category, SPU, SKU, SPUStatus, ProductMedia
from apps.goods.views.admin_import_export import _save_file_to_webp, _parse_crop_ratio
from apps.goods.media_service import MediaService
from apps.goods.services import GoodsCacheService

_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff'}

# xlsx 列名 → 内部字段（与后台 Excel 导入一致）
XLSX_COL = {
    'sku编码': 'sku', 'sku': 'sku', 'sku_code': 'sku',
    '产品型号': 'model', '型号': 'model', 'model': 'model',
    '原价': 'price', 'price': 'price', '销售价': 'price',
    '现价': 'discount_price', '折扣价': 'discount_price', '优惠价': 'discount_price',
    '标题': 'name', 'name': 'name', '商品名': 'name', '产品名称': 'name',
    '详情描述': 'description', 'description': 'description', '详情': 'description',
    '服务': 'services', 'service': 'services',
}

# 英文分类树：3 个一级分类，替代原 Optimize / Automate / Launch 营销分类
CATEGORY_TREE = {
    'Laser Engravers': ['LP1', 'LP2', 'LP2 Plus', 'LP4', 'LP5', 'LX2', 'LX2 40W Kit'],
    'Accessories': ['Cutting Beds', 'Safety Enclosures', 'Rotary Systems',
                    'Power & Filters', 'Add-ons'],
    'Materials & Blanks': ['Material Packs', 'Wooden Blanks', 'Metal Blanks',
                            'Jewelry Blanks', 'Leather & PU', 'Labels & Stickers',
                            'Drinkware & Home'],
}

# 图片子目录名 → (一级分类, 二级分类)
FOLDER_TO_CATEGORY = {
    'LP1': ('Laser Engravers', 'LP1'),
    'LP2': ('Laser Engravers', 'LP2'),
    'LP2 plus': ('Laser Engravers', 'LP2 Plus'),
    'LP4': ('Laser Engravers', 'LP4'),
    'LP5': ('Laser Engravers', 'LP5'),
    'LX2': ('Laser Engravers', 'LX2'),
    'LX2 diode': ('Laser Engravers', 'LX2 40W Kit'),
    'LaserPecker Honeycomb Cutting Bed': ('Accessories', 'Cutting Beds'),
    'LP5 Safety Enclosure': ('Accessories', 'Safety Enclosures'),
    'Electric Roller – 3-in-1 Rotary System': ('Accessories', 'Rotary Systems'),
    'Rotary Extension': ('Accessories', 'Rotary Systems'),
    'Air Purifier': ('Accessories', 'Power & Filters'),
    'PowerPack': ('Accessories', 'Power & Filters'),
    'Bluetooth': ('Accessories', 'Add-ons'),
    'Engraving Button': ('Accessories', 'Add-ons'),
    'Slide Extension': ('Accessories', 'Add-ons'),
    'Storage Bag for LP2  LP3': ('Accessories', 'Add-ons'),
    'Laser Materials Pack': ('Materials & Blanks', 'Material Packs'),
    'Metal Laser Material Pack': ('Materials & Blanks', 'Material Packs'),
    'LaserPecker LP4': ('Materials & Blanks', 'Material Packs'),
    'Holiday Maker Bundle': ('Materials & Blanks', 'Material Packs'),
    'Wooden Laser Material Pack': ('Materials & Blanks', 'Material Packs'),
    'Basswood Plywood Sheets': ('Materials & Blanks', 'Wooden Blanks'),
    'Craft Paper Sheets': ('Materials & Blanks', 'Wooden Blanks'),
    'Cinnamon Leaf': ('Materials & Blanks', 'Wooden Blanks'),
    'Bottle Opener': ('Materials & Blanks', 'Wooden Blanks'),
    'Walnut Keychain20pcs': ('Materials & Blanks', 'Wooden Blanks'),
    'Wooden Keychain40pcs': ('Materials & Blanks', 'Wooden Blanks'),
    'Cherry Keychain': ('Materials & Blanks', 'Wooden Blanks'),
    'Random Keychain': ('Materials & Blanks', 'Wooden Blanks'),
    'Shield-shaped Keychains': ('Materials & Blanks', 'Wooden Blanks'),
    'Wooden Rollerball Pen': ('Materials & Blanks', 'Wooden Blanks'),
    'Brass Coins': ('Materials & Blanks', 'Metal Blanks'),
    'Aluminum Business Cards': ('Materials & Blanks', 'Metal Blanks'),
    'Multicolor Business Cards': ('Materials & Blanks', 'Metal Blanks'),
    'Credit Card Case': ('Materials & Blanks', 'Metal Blanks'),
    'Rectangular Keychain': ('Materials & Blanks', 'Jewelry Blanks'),
    'Army Pendant Necklace': ('Materials & Blanks', 'Jewelry Blanks'),
    'Bar Necklace': ('Materials & Blanks', 'Jewelry Blanks'),
    'Cross Pendant Necklace': ('Materials & Blanks', 'Jewelry Blanks'),
    'Heart-Shaped Necklace': ('Materials & Blanks', 'Jewelry Blanks'),
    'Cuff Bracelets': ('Materials & Blanks', 'Jewelry Blanks'),
    'Stainless Steel Bracelet': ('Materials & Blanks', 'Jewelry Blanks'),
    'Leather Bracelet': ('Materials & Blanks', 'Jewelry Blanks'),
    'Card Holder': ('Materials & Blanks', 'Leather & PU'),
    'Rectangular PU Labels': ('Materials & Blanks', 'Leather & PU'),
    'Circular PU Labels': ('Materials & Blanks', 'Leather & PU'),
    'Mouse Pad': ('Materials & Blanks', 'Leather & PU'),
    'Cork Coasters': ('Materials & Blanks', 'Labels & Stickers'),
    'Coasters Circle': ('Materials & Blanks', 'Labels & Stickers'),
    'Coasters Square': ('Materials & Blanks', 'Labels & Stickers'),
    'Corkwood Label Stickers': ('Materials & Blanks', 'Labels & Stickers'),
    'Round Label Stickers': ('Materials & Blanks', 'Labels & Stickers'),
    'Label Stickers Sheet': ('Materials & Blanks', 'Labels & Stickers'),
    'Tumbler': ('Materials & Blanks', 'Drinkware & Home'),
    'Funnel and Cups': ('Materials & Blanks', 'Drinkware & Home'),
}


# 个别「型号同名 / 文件夹名与标题不一致」的显式匹配线索。
# key=图片子目录名；value 为候选词，命中即取（比通用启发式优先）。
FOLDER_MATCH_HINT = {
    'LX2 diode': ['lx2', '40w'],
}


def _norm(s):
    """归一化字符串：小写、去空白与特殊符号（用于标题/文件名比对）。"""
    s = (s or '').lower().strip()
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', s)


def _backend_root():
    # 本文件位于 <backend>/apps/goods/management/commands/，
    # 从 commands/ 目录向上 4 级（management → goods → apps → backend）即 backend 根
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *(['..'] * 4)))


class Command(BaseCommand):
    help = '幂等导入初始商品（xlsx + 图片目录）'

    def add_arguments(self, parser):
        parser.add_argument('--env', type=str, default='dev', help='环境标识（为兼容 setup.sh 调用，不参与逻辑）')
        parser.add_argument('--seed-dir', type=str, default='',
                            help='数据源目录（默认取环境变量 SEED_PRODUCTS_DIR，'
                                 '未设则为 <backend>/seed_products）')
        parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        # 优先级：命令行 > 环境变量 SEED_PRODUCTS_DIR（便于把数据源放到项目外，
        # 如 /opt/apps/seed_products，不随代码/镜像分发）> 默认 <backend>/seed_products
        seed_dir = (options['seed_dir']
                    or os.getenv('SEED_PRODUCTS_DIR', '')
                    or os.path.join(_backend_root(), 'seed_products'))
        xlsx_path = os.path.join(seed_dir, 'products.xlsx')
        images_root = self._resolve_images_root(seed_dir)

        if not os.path.isfile(xlsx_path):
            self.stdout.write(self.style.ERROR(f'未找到种子 xlsx: {xlsx_path}'))
            self.stdout.write(self.style.WARNING('跳过初始商品导入（非阻断）'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'=== 初始商品导入 seed_products ({"DRY RUN" if dry_run else "ENV=prod"}) ==='))
        self.stdout.write(f'数据源: {seed_dir}')

        # ── 0. 解析 xlsx ──
        rows = self._parse_xlsx(xlsx_path)
        if not rows:
            self.stdout.write(self.style.WARNING('xlsx 无有效数据，跳过'))
            return
        self.stdout.write(f'xlsx 商品行: {len(rows)}')

        # ── 1. 品牌 ──
        brand = None
        if not dry_run:
            brand, _ = Brand.objects.get_or_create(name='LaserPecker', defaults={'is_active': True})
            # 平台品牌 CarveNex：后台品牌管理（AdminBrands）展示用；logo 由前端静态资源兜底显示
            Brand.objects.get_or_create(
                name='CarveNex',
                defaults={'description': 'CarveNex 官方平台', 'is_active': True},
            )
        else:
            self.stdout.write('  [brand] 预览确保: LaserPecker / CarveNex')

        # ── 2. 分类树 ──
        self._ensure_categories(dry_run)

        # ── 3. 逐商品导入 ──
        folder_list = sorted(
            d for d in os.listdir(images_root) if os.path.isdir(os.path.join(images_root, d))
        ) if os.path.isdir(images_root) else []
        self.stdout.write(f'图片目录商品数: {len(folder_list)}')

        created = skipped = no_img = fixed = 0
        for folder in folder_list:
            mapping = FOLDER_TO_CATEGORY.get(folder)
            if not mapping:
                self.stdout.write(self.style.WARNING(f'  [SKIP] 无分类配置: {folder}'))
                continue
            cat_root_name, cat_child_name = mapping
            row = self._resolve_row(folder, rows)
            if row is None:
                self.stdout.write(self.style.WARNING(f'  [SKIP] 未匹配到 xlsx 行: {folder}'))
                continue
            result = self._import_one(
                folder, row, brand, cat_root_name, cat_child_name, images_root, dry_run)
            if result == 'skip':
                skipped += 1
            elif result == 'noimg':
                no_img += 1
            elif result == 'created':
                created += 1
            elif result == 'media_fixed':
                fixed += 1
            # 'noop'（预览/分类缺失）不计数

        after = '预览' if dry_run else '完成'
        self.stdout.write(self.style.SUCCESS(
            f'\n=== {after}: 新建 {created}, 已存在跳过 {skipped}, '
            f'无图 {no_img}, 补回媒体 {fixed} ==='))

    # ── xlsx 解析 ──
    def _parse_xlsx(self, path):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        headers = [str(c.value).strip() if c.value is not None else '' for c in ws[1]]
        rows = []
        for r in range(2, ws.max_row + 1):
            rec = {}
            for c, h in enumerate(headers, start=1):
                if not h:
                    continue
                field = XLSX_COL.get(h.strip().lower(), h.strip())
                val = ws.cell(r, c).value
                rec[field] = '' if val is None else str(val)
            if rec.get('name'):
                rows.append(rec)
        return rows

    def _resolve_row(self, folder, rows):
        """把图片目录匹配到 xlsx 行：
        1) 有 FOLDER_MATCH_HINT 则按候选词全命中优先；
        2) 否则型号完全相等优先，其次标题包含归一化目录名。
        """
        hint = FOLDER_MATCH_HINT.get(folder)
        fn = _norm(folder)
        hits = []
        for i, row in enumerate(rows):
            title_n = _norm(row.get('name', ''))
            model_n = _norm(row.get('model', ''))
            if hint:
                if all(k in title_n for k in hint):
                    hits.append((0, i, row))
            elif model_n and model_n == fn:
                hits.append((0, i, row))
            elif fn and fn in title_n:
                hits.append((1, i, row))
        if not hits:
            return None
        hits.sort(key=lambda t: (t[0], t[1]))
        return hits[0][2]

    # ── 分类树 ──
    def _ensure_categories(self, dry_run):
        for root_name, children in CATEGORY_TREE.items():
            if dry_run:
                self.stdout.write(f'  [分类] (DRY) 确保: {root_name} → {", ".join(children)}')
                continue
            from django.contrib.auth import get_user_model
            admin = get_user_model().objects.filter(is_superuser=True).first()
            root, _ = Category.objects.get_or_create(
                name=root_name, level=1, parent=None,
                defaults={'is_active': True, 'created_by': admin})
            for child in children:
                Category.objects.get_or_create(
                    name=child, level=2, parent=root,
                    defaults={'is_active': True, 'created_by': admin})
        if not dry_run:
            self.stdout.write('  [分类] 确保分类树完成')

    # ── 单个商品导入 ──
    def _import_one(self, folder, row, brand, cat_root_name, cat_child_name,
                    images_root, dry_run):
        name = row['name']
        if dry_run:
            self.stdout.write(f'  [DRY] 将创建 SPU: {name[:40]} → {cat_child_name}')
            return 'noop'

        # 幂等：按「中文名(name) 或 英文标准列(name_en)」匹配，soft 删除的也算已存在，
        # 避免因名称语言不一致（后台中文名 vs xlsx 英文名）导致每次重启重复建 SPU。
        dup_spu = SPU.objects.filter(
            Q(name=name) | Q(name_en=name),
            deleted_at__isnull=True,
        ).first()
        if dup_spu is not None:
            # 幂等：不重复建 SPU。但若媒体文件已丢失（例如更换/清空 media 卷，
            # 而数据库里的 ProductMedia 记录仍在），则补齐文件并重建记录，
            # 避免部署后出现「商品有数据但没有图」。
            if self._media_files_missing(dup_spu):
                folder_path = os.path.normpath(os.path.join(images_root, folder))
                self.stdout.write(
                    self.style.WARNING(f'  [修复] 媒体文件缺失，重新导入: {name[:40]}')
                )
                dup_spu.media.all().delete()
                count = self._import_images(dup_spu, folder_path)
                if count:
                    MediaService.sync_main_image(spu_id=dup_spu.id)
                    GoodsCacheService.invalidate_spu_list()
                    self.stdout.write(f'  ~ {name[:40]} 补回 {count} 张图')
                    return 'media_fixed'
            self.stdout.write(f'  [SKIP] 已存在 SPU: {name[:40]}')
            return 'skip'

        root = Category.objects.get(name=cat_root_name, level=1, parent=None)
        child = Category.objects.filter(name=cat_child_name, level=2, parent=root).first()
        if child is None:
            self.stdout.write(self.style.WARNING(f'  [SKIP] 分类不存在: {cat_child_name}'))
            return 'noop'

        spu = SPU.objects.create(
            name=name,
            brand=brand,
            category=child,
            description=row.get('description', ''),
            name_en=name,
            description_en=row.get('description', ''),
            tags=self._split_services(row.get('services', '')),
            status=SPUStatus.ON_SALE,
            product_kind='physical',
        )
        price = self._parse_price(row.get('price')) or 0
        disc = self._parse_price(row.get('discount_price'))
        SKU.objects.create(
            spu=spu,
            spec_values={},
            price=price,
            discount_price=disc if disc and disc > 0 else None,
            # 确定性初始化库存：避免 stock=0 导致前台“无货”无法加购。
            # 基于标题 zlib.crc32 稳定取 50~500（跨进程/跨机器一致，保证可复现）。
            stock=50 + (zlib.crc32(name.encode('utf-8')) % 451),
            shelf_status='on',
        )

        folder_path = os.path.normpath(os.path.join(images_root, folder))
        count = self._import_images(spu, folder_path)
        if count == 0:
            self.stdout.write(self.style.WARNING(f'  [媒体] 无图片: {name[:40]}'))
            return 'noimg'
        MediaService.sync_main_image(spu_id=spu.id)
        GoodsCacheService.invalidate_spu_list()
        self.stdout.write(f'  + {name[:40]} ({count} 图)')
        return 'created'

    @staticmethod
    def _resolve_images_root(seed_dir):
        """确定图片根目录：优先环境变量 SEED_IMAGES_SUBDIR，其次探测常见名称。

        支持把图片目录命名为 images / product_pic / pics 等，结构统一为
        <图片目录>/<产品名>/<图片文件>（例如 product_pic/产品名1/）。
        """
        preferred = os.getenv('SEED_IMAGES_SUBDIR', '').strip()
        candidates = []
        if preferred:
            candidates.append(preferred)
        candidates += ['images', 'product_pic', 'pics', '图片']
        for name in candidates:
            path = os.path.join(seed_dir, name)
            if os.path.isdir(path):
                return path
        return os.path.join(seed_dir, candidates[0])

    @staticmethod
    def _media_files_missing(spu) -> bool:
        """判断 SPU 的媒体文件是否在磁盘上真实缺失。

        只查 ProductMedia 记录是不够的：清空 media 卷后记录仍在、文件已丢，
        此时必须按物理文件是否存在判定，才能触发自动补回。

        安全约束（避免误判导致每次启动都重导）：
        - MEDIA_ROOT 未配置时一律返回 False（视为未缺失）；
        - 绝对 URL（如 CDN）无法本地校验，同样视为存在；
        - 无任何媒体记录时才判定为缺失（需要补图）。
        """
        from django.conf import settings

        media_root = getattr(settings, 'MEDIA_ROOT', '') or ''
        if not media_root:
            return False

        qs = spu.media.filter(status='active')
        if not qs.exists():
            return True
        for m in qs:
            url = m.list_url or m.thumb_url or ''
            if not url.startswith('/media/'):
                continue
            rel = url[len('/media/'):]
            if not os.path.isfile(os.path.join(media_root, rel)):
                return True
        return False

    def _split_services(self, text):
        return [t for t in re.split(r'[，,、;；|｜/／\n\r]+', text or '') if t.strip()]

    def _parse_price(self, value):
        """把价格字符串解析成数值：支持 '$9.99'、'9.99'、'19.9/59.9'（区间取第一档）。

        返回 float，失败返回 0；discount_price 为 0/空则返回 None（表示无折扣）。
        """
        s = str(value or '').strip()
        if not s:
            return None
        # 取区间第一档（如 '9.99/19.99' → 9.99）
        first = re.split(r'[/／]', s, maxsplit=1)[0]
        m = re.search(r'(\d+(?:\.\d+)?)', first)
        if not m:
            return None
        return float(m.group(1))

    def _import_images(self, spu, folder_path):
        if not os.path.isdir(folder_path):
            return 0
        files = sorted(f for f in os.listdir(folder_path)
                       if os.path.splitext(f)[1].lower() in _IMAGE_EXTS)
        count = 0
        crop = _parse_crop_ratio('1:1')
        for f in files:
            try:
                fpath = os.path.join(folder_path, f)
                urls = _save_file_to_webp(fpath, crop_ratio=crop)
                ProductMedia.objects.create(
                    spu=spu, media_type='image', sort_order=count, status='active',
                    file_size=os.path.getsize(fpath),
                    thumb_url=urls['thumb_url'], list_url=urls['list_url'],
                    large_url=urls['large_url'], original_url=urls['original_url'],
                )
                count += 1
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f'    图片失败 {f}: {e}'))
        return count