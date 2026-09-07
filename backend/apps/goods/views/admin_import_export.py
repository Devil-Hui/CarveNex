import csv
import io
import logging
import os
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes
from django.http import StreamingHttpResponse
from django.conf import settings

from utils.api_base_view import BaseApiView
from utils.response_codes import Messages
from ..models import SPU, SPUStatus, SKU, Brand, Category, ProductMedia
from apps.rbac.permissions import HasPerm
from apps.rbac.services import has_role
from apps.rbac.constants import Role
from ..admin_permissions import get_group_managed_category_ids
from utils.upload_security import UploadValidationError, parse_csv_upload, escape_csv_cell
from ..media_service import MediaService

_logger = logging.getLogger('biz')

_VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.m4v', '.avi'}
_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff'}
# zip 内单文件解压上限（防护 zip 炸弹），单位字节
_ZIP_SINGLE_FILE_MAX = 200 * 1024 * 1024
# zip 内允许的文件总数上限
_ZIP_MAX_ENTRIES = 1000

# Excel 列名 → 内部字段映射（兼容中英文表头）
COLUMN_MAP = {
    'sku编码': 'sku_code', 'sku': 'sku_code', 'sku_code': 'sku_code',
    '产品型号': 'model', '型号': 'model', 'model': 'model',
    '原价': 'price', 'price': 'price',
    '现价': 'discount_price', 'discount_price': 'discount_price',
    '标题': 'name', '商品名': 'name', 'name': 'name',
    '详情描述': 'description', '描述': 'description', 'description': 'description',
    '服务': 'services', 'service': 'services',
}


def _parse_upload_rows(uploaded):
    """解析上传文件为行字典列表，支持 xlsx / csv。"""
    filename = (uploaded.name or '').lower()
    if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
        return _parse_xlsx(uploaded)
    return parse_csv_upload(uploaded)


def _parse_xlsx(uploaded):
    """用 openpyxl 解析 xlsx，返回 [{列名: 值}]。"""
    import openpyxl
    uploaded.seek(0)
    wb = openpyxl.load_workbook(uploaded, data_only=True)
    ws = wb.active
    if ws.max_row < 2:
        return []
    headers = []
    for cell in ws[1]:
        headers.append(str(cell.value).strip() if cell.value is not None else '')
    rows = []
    for r in range(2, ws.max_row + 1):
        row = {}
        for c, header in enumerate(headers, start=1):
            if not header:
                continue
            val = ws.cell(r, c).value
            row[header] = '' if val is None else str(val)
        if any(v.strip() for v in row.values()):
            rows.append(row)
    return rows


def _normalize_row(row):
    """将原始行（任意表头）映射为内部字段。"""
    out = {}
    for raw_key, value in row.items():
        key = COLUMN_MAP.get((raw_key or '').strip().lower(), (raw_key or '').strip())
        if key not in out or not out[key]:
            out[key] = (value or '').strip()
    return out


def _split_services(services_text):
    """把服务列文本按换行拆成标签列表（忽略空行）。"""
    tags = []
    for line in (services_text or '').split('\n'):
        line = line.strip()
        if line:
            tags.append(line)
    return tags


def _save_image_to_spu(spu, upload_file, sort_order):
    """把单张原始图片转成四尺寸 WebP 并挂到 SPU 的 ProductMedia。

    复用 MediaCreateView 的转码逻辑（thumb/list/large/original 四尺寸）。
    返回 (ok, error)。
    """
    from io import BytesIO
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from PIL import Image, ImageOps
    from utils.storage import media_key
    from ..models import ProductMedia
    from ..media_service import MediaService
    from ..services import GoodsCacheService

    WEBP_QUALITY = 90
    try:
        upload_file.seek(0)
        with Image.open(upload_file) as img:
            img = ImageOps.exif_transpose(img)
            img.load()
            if img.mode in ('RGBA', 'LA', 'P', 'PA'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            def _save_size(size):
                buf = BytesIO()
                resized = img.copy()
                if size:
                    resized.thumbnail((size, size), Image.LANCZOS)
                resized.save(buf, 'WEBP', lossless=False, quality=WEBP_QUALITY, method=4)
                buf.seek(0)
                path = default_storage.save(media_key('products', '.webp'), ContentFile(buf.getvalue()))
                return default_storage.url(path)

            thumb_url = _save_size(200)
            list_url = _save_size(400)
            large_url = _save_size(800)
            original_url = _save_size(0)

        total_size = upload_file.size
        ProductMedia.objects.create(
            spu=spu,
            media_type='image',
            thumb_url=thumb_url,
            list_url=list_url,
            large_url=large_url,
            original_url=original_url,
            sort_order=sort_order,
            status='active',
            file_size=total_size,
        )
        MediaService.sync_main_image(spu.id)
        GoodsCacheService.invalidate_media_list(spu.id)
        GoodsCacheService.invalidate_spu(spu.id)
        GoodsCacheService.invalidate_spu_list()
        return True, ''
    except Exception as e:  # noqa: BLE001
        _logger.warning('导入图片处理失败 spu=%s: %s', spu.id, e)
        return False, str(e)


def _match_images_to_spu(images, spu_name):
    """按商品名匹配图片文件（文件名前缀包含商品名）。返回匹配的图片列表。"""
    name = (spu_name or '').strip().lower()
    if not name:
        return []
    matched = []
    for f in images:
        fname = (f.name or '').lower()
        # 文件名前缀匹配商品名（忽略扩展名）
        base = fname.rsplit('.', 1)[0] if '.' in fname else fname
        if name in base or base in name:
            matched.append(f)
    return matched


class ImportProductsView(BaseApiView):
    """Excel/CSV 导入商品 — 上传 → 预览 → 确认导入。

    支持列：sku编码、产品型号、原价、现价、标题、详情描述、服务。
    一行 = 一个 SPU + 一个 SKU；服务列按换行拆成标签；导入后创建草稿。
    图片/视频可选：按商品名匹配图片文件（文件名前缀包含商品名）。
    """
    permission_classes = [HasPerm('goods.import.execute')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiResponse(description='Import result')}
    )
    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': Messages.ADMIN_IMPORT_INVALID_FORMAT}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_rows = _parse_upload_rows(uploaded)
        except UploadValidationError:
            return Response({'detail': Messages.ADMIN_IMPORT_PREVIEW_FAILED}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:  # noqa: BLE001
            _logger.warning('导入文件解析失败: %s', e)
            return Response({'detail': Messages.ADMIN_IMPORT_PREVIEW_FAILED}, status=status.HTTP_400_BAD_REQUEST)

        rows = [_normalize_row(r) for r in raw_rows]
        rows = [r for r in rows if r.get('name')]
        if not rows:
            return Response({'detail': Messages.ADMIN_IMPORT_NO_DATA}, status=status.HTTP_400_BAD_REQUEST)

        # 预览模式：返回解析结果
        if request.data.get('preview') == 'true':
            preview = []
            errors = []
            for i, row in enumerate(rows):
                row_errors = []
                if not row.get('name'):
                    row_errors.append('Name is required')
                preview.append({
                    'row': i + 1,
                    'name': row.get('name', ''),
                    'model': row.get('model', ''),
                    'price': row.get('price', ''),
                    'discount_price': row.get('discount_price', ''),
                    'sku_code': row.get('sku_code', ''),
                    'description': row.get('description', ''),
                    'tags': _split_services(row.get('services', '')),
                    'valid': len(row_errors) == 0,
                    'errors': row_errors,
                })
                if row_errors:
                    errors.extend([f'Row {i+1}: {e}' for e in row_errors])

            return Response({
                'preview': preview,
                'total_rows': len(rows),
                'valid_rows': sum(1 for r in preview if r['valid']),
                'error_count': len(errors),
                'errors': errors[:20],
            })

        # 确认导入模式 —— 品牌/分类必须显式选择，不再静默回退到"首个"默认数据
        brand_id = request.data.get('brand_id')
        category_id = request.data.get('category_id')
        brand = None
        category = None
        if brand_id:
            brand = Brand.objects.filter(id=brand_id, is_active=True).first()
        if category_id:
            category = Category.objects.filter(id=category_id, is_active=True).first()
        if not brand:
            return Response({'detail': '请选择品牌（默认不再自动选用）'}, status=status.HTTP_400_BAD_REQUEST)
        if not category:
            return Response({'detail': '请选择分类（默认不再自动选用）'}, status=status.HTTP_400_BAD_REQUEST)

        # 图片文件夹：按商品名匹配（文件名前缀包含商品名）
        images = request.FILES.getlist('images')

        imported = 0
        errors = []
        for i, row in enumerate(rows):
            try:
                name = row.get('name', '')
                if not name:
                    continue
                if not brand or not category:
                    errors.append(f'Row {i+1}: 缺少品牌或分类')
                    continue

                # 需求调整：导入商品直接上架（ON_SALE），前台实时可见（超管导入）。
                spu = SPU.objects.create(
                    name=name,
                    brand=brand,
                    category=category,
                    description=row.get('description', ''),
                    tags=_split_services(row.get('services', '')),
                    status=SPUStatus.ON_SALE,
                )

                # 创建 SKU：产品型号作为规格值，原价/现价映射 price/discount_price
                spec_values = {}
                if row.get('model'):
                    spec_values['型号'] = row['model']
                SKU.objects.create(
                    spu=spu,
                    spec_values=spec_values,
                    price=float(row['price']) if row.get('price') else 0,
                    discount_price=float(row['discount_price']) if row.get('discount_price') else None,
                    stock=0,
                    sku_code=row.get('sku_code', ''),
                    shelf_status='on',
                )

                # 按商品名匹配图片并上传（图片按文件名顺序）
                if images:
                    matched = _match_images_to_spu(images, name)
                    for sort_idx, img_file in enumerate(matched):
                        _save_image_to_spu(spu, img_file, sort_idx)

                imported += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f'Row {i+1}: {str(e)}')

        return Response({
            'message': Messages.SUCCESS,
            'imported': imported,
            'errors': errors[:20],
        }, status=status.HTTP_201_CREATED)


class ExportProductsView(BaseApiView):
    """CSV 导出商品"""
    permission_classes = [HasPerm('goods.import.execute')]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(description='CSV file')}
    )
    def post(self, request):
        qs = (
            SPU.objects.filter(deleted_at__isnull=True)
            .select_related('brand', 'category')
        )
        # 数据权限：非超管仅能导出本组类目下的商品（DB 层行级过滤）
        if not has_role(request.user, Role.SUPERADMIN.value):
            managed_ids = get_group_managed_category_ids(request.user)
            qs = qs.filter(category_id__in=managed_ids) if managed_ids else qs.none()

        # 敏感操作审计：导出必须留痕（含行级范围）
        is_admin = has_role(request.user, Role.SUPERADMIN.value)
        from .admin_audit import create_audit_log
        create_audit_log(
            request.user, 'export_products', 'spu', 0,
            changes={'count': qs.count(), 'scope': 'managed' if not is_admin else 'all'},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # 大数据量导出必须流式（StreamingHttpResponse + 分块迭代）：
        # 仅保留一个 chunk（默认 500 行）在内存，10 万条记录也不会 OOM，
        # 且 chunked Transfer-Encoding 交付，第一块数据即可开始传输。
        response = StreamingHttpResponse(
            self._stream_rows(qs), content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
        return response

    # 每块最多物化多少条 SPU 到内存（内存上界 = chunk * 单行开销）
    EXPORT_CHUNK_SIZE = 500

    @classmethod
    def _csv_line(cls, row: list) -> str:
        """将一行 render 为合法 CSV 文本（含换行）。"""
        buf = io.StringIO()
        csv.writer(buf).writerow(row)
        return buf.getvalue()

    @classmethod
    def _stream_rows(cls, spu_qs):
        """惰性生成 CSV 文本，按块加载 SPU 及其 SKU，内存恒定。"""
        yield cls._csv_line(['Name', 'Brand', 'Category', 'Price', 'Stock', 'Status', 'Description', 'Main Image', 'Created At'])

        iterator = spu_qs.iterator(chunk_size=cls.EXPORT_CHUNK_SIZE)
        chunk = []
        for spu in iterator:
            chunk.append(spu)
            if len(chunk) >= cls.EXPORT_CHUNK_SIZE:
                yield from cls._render_chunk(chunk)
                chunk = []
        if chunk:
            yield from cls._render_chunk(chunk)

    @classmethod
    def _render_chunk(cls, chunk):
        """渲染一个 chunk：批量取 SKU（避免逐条 N+1），逐行输出。"""
        id_list = [s.id for s in chunk]
        sku_map = {
            sku.spu_id: sku
            for sku in SKU.objects.filter(spu_id__in=id_list)
        }
        for spu in chunk:
            sku = sku_map.get(spu.id)
            price = str(sku.price) if sku else ''
            stock = str(sku.stock) if sku else ''
            category_path = cls._get_category_path(spu.category)
            yield cls._csv_line([
                escape_csv_cell(spu.name), escape_csv_cell(spu.brand.name), escape_csv_cell(category_path),
                price, stock, spu.status,
                escape_csv_cell(spu.description), escape_csv_cell(spu.main_image or ''),
                spu.created_at.strftime('%Y-%m-%d %H:%M:%S') if spu.created_at else '',
            ])

    @staticmethod
    def _get_category_path(category):
        parts = []
        current = category
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return ' / '.join(parts)


# ==================== zip 批量导入图片/视频 ====================

def _parse_crop_ratio(value):
    """解析裁切比例，如 '1:1' / '3:4' / '4:5' → (w, h)。
    返回 None 表示不裁切（保持原比例）。
    默认商品主图为 1:1 正方形（前端主图通常正方形）。
    """
    if not value:
        return (1, 1)
    text = str(value).strip().lower()
    if text in ('none', '0', 'original', ''):
        return None
    try:
        parts = text.replace('：', ':').split(':')
        if len(parts) != 2:
            return (1, 1)
        return (int(parts[0]), int(parts[1]))
    except (TypeError, ValueError):
        return (1, 1)


def _save_file_to_webp(src_path, *, crop_ratio):
    """把磁盘上的图片文件转成四尺寸 WebP（可选居中裁切），保存到 default_storage。

    返回 dict 四个尺寸 URL；解压文件不占用 DB 连接的 worker 线程内调用。
    """
    from io import BytesIO
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from PIL import Image, ImageOps
    from utils.storage import media_key

    WEBP_QUALITY = 90
    with Image.open(src_path) as img:
        img = ImageOps.exif_transpose(img)
        img.load()
        # 居中裁切到目标比例（先放大到短板满足再切）：
        # 只裁一次 → 四尺寸复用同一张处理好的图，避免重复解码，批效能高。
        if crop_ratio:
            target_w, target_h = crop_ratio
            src_w, src_h = img.size
            if target_w and target_h:
                scale = max(src_w / target_w, src_h / target_h)
                new_w = max(1, round(src_w / scale))
                new_h = max(1, round(src_h / scale))
                img = img.resize((new_w, new_h), Image.LANCZOS)
                # 居中裁剪到目标比例
                if new_w / new_h != target_w / target_h:
                    if new_w / new_h > target_w / target_h:  # 太宽 → 裁左右
                        cut_w = round(new_h * target_w / target_h)
                        left = (new_w - cut_w) // 2
                        box = (left, 0, left + cut_w, new_h)
                    else:  # 太高 → 裁上下
                        cut_h = round(new_w * target_h / target_w)
                        top = (new_h - cut_h) // 2
                        box = (0, top, new_w, top + cut_h)
                    img = img.crop(box)
        if img.mode in ('RGBA', 'LA', 'P', 'PA'):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        def _save_size(size):
            buf = BytesIO()
            resized = img
            if size:
                resized = img.copy()
                resized.thumbnail((size, size), Image.LANCZOS)
            resized.save(buf, 'WEBP', lossless=False, quality=WEBP_QUALITY, method=4)
            buf.seek(0)
            path = default_storage.save(media_key('products', '.webp'), ContentFile(buf.getvalue()))
            return default_storage.url(path)

        return {
            'thumb_url': _save_size(200),
            'list_url': _save_size(400),
            'large_url': _save_size(800),
            'original_url': _save_size(0),
        }


def _save_video_to_storage(src_path, dest_name):
    """原样保存视频文件到 default_storage，返回 URL。

    无需 ffmpeg——不生成头帧（ProductMedia.video_*_url 留空，前端展示原视频）。
    """
    from django.core.files.storage import default_storage
    from utils.storage import media_key

    ext = os.path.splitext(dest_name)[1].lower() or '.mp4'
    with open(src_path, 'rb') as f:
        path = default_storage.save(media_key('products/video', ext), f)
    return default_storage.url(path)


def _process_one_folder(folder_name, folder_path, spu_map, ratio):
    """处理 zip 里的一个产品文件夹。

    folder_name = SPU.name。返回该产品的导入统计。
    """
    result = {'folder': folder_name, 'images': 0, 'videos': 0, 'errors': []}
    spu = spu_map.get(folder_name)
    if spu is None:
        result['errors'].append('未找到同名的 SPU（请先导入商品 Excel）')
        return result

    # 图片裁切比例
    crop = _parse_crop_ratio(ratio)

    # 收集图片和视频（按文件名自然排序保证 5 图顺序稳定）
    images = []
    videos = []
    for fname in sorted(os.listdir(folder_path)):
        fpath = os.path.join(folder_path, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext in _IMAGE_EXTS:
            images.append(fpath)
        elif ext in _VIDEO_EXTS:
            videos.append(fpath)

    # 数量上限（settings.MEDIA_MAX_IMAGES_PER_SPU 默认 5，视频默认 1）
    max_img = getattr(settings, 'MEDIA_MAX_IMAGES_PER_SPU', 5)
    max_vid = getattr(settings, 'MEDIA_MAX_VIDEOS_PER_SPU', 1)

    # 图片
    for fpath in images[:max_img]:
        try:
            urls = _save_file_to_webp(fpath, crop_ratio=crop)
            ProductMedia.objects.create(
                spu=spu,
                media_type='image',
                thumb_url=urls['thumb_url'],
                list_url=urls['list_url'],
                large_url=urls['large_url'],
                original_url=urls['original_url'],
                sort_order=result['images'],
                status='active',
                file_size=os.path.getsize(fpath),
            )
            result['images'] += 1
        except Exception as e:  # noqa: BLE001
            result['errors'].append(f'图片 {os.path.basename(fpath)}: {e}')

    # 视频
    for fpath in videos[:max_vid]:
        try:
            video_url = _save_video_to_storage(fpath, os.path.basename(fpath))
            ProductMedia.objects.create(
                spu=spu,
                media_type='video',
                video_url=video_url,
                sort_order=result['videos'],
                status='active',
                file_size=os.path.getsize(fpath),
            )
            result['videos'] += 1
        except Exception as e:  # noqa: BLE001
            result['errors'].append(f'视频 {os.path.basename(fpath)}: {e}')

    if result['images'] or result['videos']:
        MediaService.sync_main_image(spu.id)
    from ..services import GoodsCacheService
    GoodsCacheService.invalidate_spu(spu.id)
    GoodsCacheService.invalidate_media_list(spu.id)
    GoodsCacheService.invalidate_spu_list()
    return result


class ImportProductMediaZipView(BaseApiView):
    """批量导入商品图片/视频（zip 压缩包）。

    文件夹结构（与你的工作流一致）：
        zip 内每个顶层子文件夹 = 一个商品，文件夹名 = 商品名（SPU.name）。
        文件夹内放图片（jpg/png/webp…）和可选 1 个视频（mp4/webm/mov…）。

    流程：先导入商品 Excel 建好 SPU → 再传此 zip，按「文件夹名=SPU.name」匹配，
    图片自动转四尺寸 WebP + 可选中线裁切比例，视频原样保存（无需 ffmpeg），
    最后挂载到对应 SPU 的 ProductMedia。

    效能：图片转码是 CPU 密集，用线程池按核数并发处理多个文件夹。
    返回：每个文件夹的成功/失败统计。

    multipart 参数：
        file         必填 zip
        crop         可选裁切比例，默认 '1:1'（正方形）；'none'/'original' 表示不裁切
        concurrency  可选并发文件夹数（默认 CPU 核数-1，至少 1）
    """
    permission_classes = [HasPerm('goods.import.execute')]

    _html = True

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiResponse(description='Zip import result')}
    )
    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': '请上传 zip 压缩包'}, status=status.HTTP_400_BAD_REQUEST)

        filename = (uploaded.name or '').lower()
        if not filename.endswith('.zip'):
            return Response({'detail': '仅支持 .zip 压缩包'}, status=status.HTTP_400_BAD_REQUEST)

        ratio = request.data.get('crop') or '1:1'
        workers = int(request.data.get('workers') or max(1, (os.cpu_count() or 2) - 1))

        tmp_root = None
        try:
            tmp_root = tempfile.mkdtemp(prefix='spu_media_zip_')
            zip_path = os.path.join(tmp_root, 'upload.zip')

            # 限流写 zip 到磁盘
            with open(zip_path, 'wb') as out:
                for chunk in uploaded.chunks():
                    out.write(chunk)

            # ---------- 安全解压（zip 炸弹 + 路径穿越防护） ----------
            extract_dir = os.path.join(tmp_root, 'extract')
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    entries = zf.infolist()
                    if len(entries) > _ZIP_MAX_ENTRIES:
                        return Response({'detail': f'zip 内文件数超过限制（{_ZIP_MAX_ENTRIES}）'}, status=status.HTTP_400_BAD_REQUEST)
                    for member in entries:
                        # 防 zip 炸弹：单文件解压体积校验
                        if member.file_size > _ZIP_SINGLE_FILE_MAX:
                            return Response({'detail': f'压缩包内文件超过上限 {_ZIP_SINGLE_FILE_MAX // (1024*1024)}MB'}, status=status.HTTP_400_BAD_REQUEST)
                        # 防路径穿越（zip-slip）：目标路径必须在 extract_dir 内
                        target = os.path.join(extract_dir, member.filename)
                        target_real = os.path.normpath(target)
                        if not target_real.startswith(os.path.normpath(extract_dir + os.sep)):
                            return Response({'detail': f'非法压缩包路径: {member.filename}'}, status=status.HTTP_400_BAD_REQUEST)
                    zf.extractall(extract_dir)
            except zipfile.BadZipFile:
                return Response({'detail': '不是有效的 zip 压缩包'}, status=status.HTTP_400_BAD_REQUEST)

            # ---------- 构建 SPU 名称 → SPU 映射（文件夹名 = SPU.name） ----------
            top_level = sorted(
                d for d in os.listdir(extract_dir)
                if os.path.isdir(os.path.join(extract_dir, d))
            )
            spu_map = {
                spu.name: spu
                for spu in SPU.objects.filter(
                    name__in=top_level, deleted_at__isnull=True
                )
            }

            if not top_level:
                return Response({'detail': '压缩包内没有产品文件夹'}, status=status.HTTP_400_BAD_REQUEST)

            # ---------- 并发处理 ----------
            results = []
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_process_one_folder, folder_name, os.path.join(extract_dir, folder_name), spu_map, ratio): folder_name
                    for folder_name in top_level
                }
                for future in as_completed(futures):
                    folder_name = futures[future]
                    try:
                        results.append(future.result())
                    except Exception as e:  # noqa: BLE001
                        results.append({'folder': folder_name, 'images': 0, 'videos': 0, 'errors': [str(e)]})

            # 汇总
            imported_folders = sum(1 for r in results if r['images'] or r['videos'])
            total_images = sum(r['images'] for r in results)
            total_videos = sum(r['videos'] for r in results)
            skipped = [r['folder'] for r in results if not r['images'] and not r['videos']]

            return Response({
                'message': Messages.SUCCESS,
                'processed_folders': len(results),
                'imported_folders': imported_folders,
                'total_images': total_images,
                'total_videos': total_videos,
                'skipped': skipped,
                'details': results,
            }, status=status.HTTP_201_CREATED)
        finally:
            if tmp_root:
                shutil.rmtree(tmp_root, ignore_errors=True)