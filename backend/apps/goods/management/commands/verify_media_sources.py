"""部署前媒体来源自检 —— 验证「商品数据源 / MEDIA_ROOT / R2」是否就绪。

用途：docker 首次构建或部署前执行，确认商品图与商品表（Excel）来源配置正确，
避免部署后出现「无商品 / 商品无图」却无任何报错的静默失败。

    python manage.py verify_media_sources
    python manage.py verify_media_sources --dir /opt/apps/seed_products

数据源目录约定（可用 --dir 覆盖，或设环境变量 SEED_PRODUCTS_DIR）：
    <seed 目录>/
        products.xlsx          # 【必需】商品信息表（价格/描述等），建商品依赖它
        images/<子目录>/       # 每个子目录 = 一个商品的原图

检查项：
  1. 数据源目录是否存在、可读，products.xlsx 是否存在（必需），
     images/ 下有多少商品目录与图片
  2. 本地 MEDIA_ROOT 是否存在且可写（上传依赖）
  3. R2 凭据是否齐全、能否连通（head_bucket）；未启用则走本地回退
  4. 可选：PRODUCT_IMAGES_ROOT（import_media_dir 用的纯图片目录，不依赖 Excel）

退出码：0=全部通过；1=存在失败项（便于 CI / 部署脚本判断）。
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')


class Command(BaseCommand):
    help = '验证商品数据源（products.xlsx + images）与存储（MEDIA_ROOT / R2）是否就绪'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir', type=str, default='',
            help='数据源目录（默认取环境变量 SEED_PRODUCTS_DIR，未设则为 <backend>/seed_products）')

    def handle(self, *args, **options):
        results = []

        def report(name, ok, detail):
            results.append(ok)
            tag = self.style.SUCCESS('PASS') if ok else self.style.ERROR('FAIL')
            self.stdout.write(f'[{tag}] {name}: {detail}')

        # 1) 数据源目录（含必需 Excel）
        self.stdout.write(self.style.MIGRATE_HEADING('=== 1. 商品数据源目录 ==='))
        seed_dir = (options['dir']
                    or os.getenv('SEED_PRODUCTS_DIR', '')
                    or os.path.join(settings.BASE_DIR, 'seed_products'))
        self.stdout.write(f'路径: {seed_dir}')

        if not os.path.isdir(seed_dir):
            report('数据源目录', False,
                   f'不存在: {seed_dir}（请设置 SEED_PRODUCTS_DIR 或挂载该目录）')
        else:
            report('数据源目录', True, '存在')

            # 1a) products.xlsx —— 必需
            xlsx_path = os.path.join(seed_dir, 'products.xlsx')
            if os.path.isfile(xlsx_path):
                size_kb = round(os.path.getsize(xlsx_path) / 1024, 1)
                report('products.xlsx（必需）', True, f'存在（{size_kb} KB）')
            else:
                report('products.xlsx（必需）', False,
                       f'缺失: {xlsx_path}。seed_products 依赖它建商品，'
                       f'缺失将「非阻断跳过」→ 部署后无商品。请放入该表或改用 '
                       f'SEED_PRODUCTS_DIR 指向正确目录。')

            # 1b) images/ —— 商品原图
            images_root = os.path.join(seed_dir, 'images')
            if not os.path.isdir(images_root):
                report('images/ 目录', False, f'不存在: {images_root}')
            else:
                try:
                    folders = sorted(
                        d for d in os.listdir(images_root)
                        if os.path.isdir(os.path.join(images_root, d)) and not d.startswith('.')
                    )
                except OSError as e:
                    report('images/ 目录', False, f'无法读取: {e}')
                    folders = []
                if folders:
                    total_img = 0
                    unreadable = []
                    for d in folders:
                        try:
                            fs = os.listdir(os.path.join(images_root, d))
                        except OSError as e:
                            unreadable.append(f'{d}({e})')
                            continue
                        total_img += sum(1 for f in fs if f.lower().endswith(IMAGE_EXT))
                    if unreadable:
                        report('images/ 目录', False,
                               f'{len(unreadable)} 个子目录不可读: {unreadable[:3]}')
                    else:
                        report('images/ 目录', True,
                               f'{len(folders)} 个商品目录，{total_img} 张图片')
                else:
                    report('images/ 目录', False,
                           f'下没有商品子目录: {images_root}')

        # 2) MEDIA_ROOT
        self.stdout.write(self.style.MIGRATE_HEADING('=== 2. 本地 MEDIA_ROOT ==='))
        media_root = getattr(settings, 'MEDIA_ROOT', '') or ''
        self.stdout.write(f'路径: {media_root}')
        if not media_root:
            report('MEDIA_ROOT', False, '未配置 settings.MEDIA_ROOT')
        else:
            exists = os.path.isdir(media_root)
            writable = os.access(media_root, os.W_OK) if exists else False
            report('MEDIA_ROOT', exists and writable,
                   f'存在={exists}, 可写={writable}')

        # 3) R2
        self.stdout.write(self.style.MIGRATE_HEADING('=== 3. Cloudflare R2 ==='))
        backend = settings.STORAGES.get('default', {}).get('BACKEND', '')
        r2_enabled = 'R2DBFallbackStorage' in backend
        acct = getattr(settings, 'R2_ACCOUNT_ID', '')
        bucket = getattr(settings, 'R2_BUCKET', '')
        self.stdout.write(f'STORAGES.default = {backend}')

        if not r2_enabled:
            report('R2', True, '未启用 R2（当前存储后端非 R2），读取走本地回退')
        elif not (acct and bucket):
            report('R2', False,
                   'R2 后端已启用，但 R2_ACCOUNT_ID / R2_BUCKET 未配置完整，读取将回退本地')
        else:
            try:
                import boto3
                client = boto3.client(
                    's3',
                    endpoint_url=f'https://{acct}.r2.cloudflarestorage.com',
                    aws_access_key_id=getattr(settings, 'R2_ACCESS_KEY_ID', ''),
                    aws_secret_access_key=getattr(settings, 'R2_SECRET_ACCESS_KEY', ''),
                )
                client.head_bucket(Bucket=bucket)
                report('R2', True, f'可连通（bucket={bucket}）')
            except Exception as e:  # noqa: BLE001 - 自检需转异常为报告
                report('R2', False, f'不可达: {type(e).__name__}: {e}')

        # 4) 可选：纯图片目录（import_media_dir，不依赖 Excel）
        self.stdout.write(self.style.MIGRATE_HEADING('=== 4. 可选：PRODUCT_IMAGES_ROOT ==='))
        img_root = os.getenv('PRODUCT_IMAGES_ROOT', '')
        if not img_root:
            self.stdout.write('[INFO] 未设置（可选）。import_media_dir 用它按'
                              '「子文件夹名=商品名」导入图片，不依赖 Excel。')
        elif not os.path.isdir(img_root):
            self.stdout.write(self.style.WARNING(
                f'[WARN] 已设置但目录不存在: {img_root}（可选，不影响主流程）'))
        else:
            self.stdout.write(f'[INFO] 已设置且存在: {img_root}')

        # 汇总
        failed = results.count(False)
        self.stdout.write(self.style.MIGRATE_HEADING('=== 汇总 ==='))
        if failed:
            self.stdout.write(self.style.ERROR(f'存在 {failed} 项失败，请修正后再构建/部署。'))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('全部检查通过，可以构建/部署。'))
