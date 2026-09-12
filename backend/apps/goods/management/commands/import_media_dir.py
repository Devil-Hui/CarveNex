"""
批量导入商品图片/视频媒体 — 本地目录版
=======================================
在「本地/服务器」按文件夹批量把图片+视频落到数据库的 ProductMedia，文件夹名 = 商品名（SPU.name）。

用法:
  docker compose exec web python manage.py import_media_dir --dir=/backend/_media_import --ratio=1:1

目录结构（与 zip 导入一致）:
  <dir>/
    ¥商品名1/     # 文件夹名 = SPU.name
       1.jpg       # 图片（jpg/png/webp…），自动转四尺寸 WebP
       video.mp4   # 可选视频（mp4/webm/mov…），原样保存
    ¥商品名2/
       ...

说明:
  1. 需先确保对应名称的 SPU 已存在（可用 Excel 导入建好商品）。
  2. 每个文件夹最多导入 MEDIA_MAX_IMAGES_PER_SPU 张图、MEDIA_MAX_VIDEOS_PER_SPU 个视频。
  3. 图片可选居中裁切比例 --ratio（如 '1:1'、'4:3'、'none' 表示不裁切）。
  4. 重复执行会在同 SPU 下追加媒体（不去重），如需整批覆盖请先清理。
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand, CommandError

from apps.goods.models import SPU
from apps.goods.views.admin_import_export import _process_one_folder


class Command(BaseCommand):
    help = '从目录批量导入商品媒体（每个子文件夹=一个商品）到 ProductMedia'

    def add_arguments(self, parser):
        parser.add_argument('--dir', type=str, default='/media_import',
                            help='媒体根目录，其下每个子文件夹=一个商品（文件夹名=SPU.name）')
        parser.add_argument('--ratio', type=str, default='1:1',
                            help='图片裁切比例，默认 1:1；none/original 表示不裁切')
        parser.add_argument('--concurrency', type=int, default=0,
                            help='并发处理文件夹数，默认（CPU 核数-1，至少 1）')

    def handle(self, *args, **options):
        root = options['dir']
        if not os.path.isdir(root):
            if not os.path.isabs(root):
                root = os.path.join(os.getcwd(), root)
                if not os.path.isdir(root):
                    raise CommandError(f'目录不存在: {options["dir"]}')
            else:
                raise CommandError(f'目录不存在: {options["dir"]}')

        self.stdout.write(f'扫描目录: {root}')

        # 顶层子文件夹（排除文件与隐藏目录）
        folder_names = sorted(
            d for d in os.listdir(root)
            if os.path.isdir(os.path.join(root, d)) and not d.startswith('.')
        )
        if not folder_names:
            self.stdout.write(self.style.WARNING('根目录下没有商品文件夹'))
            return

        # 构建 文件夹名 → SPU 映射
        spu_map = {
            spu.name: spu
            for spu in SPU.objects.filter(
                name__in=folder_names, deleted_at__isnull=True
            )
        }
        missing = [f for f in folder_names if f not in spu_map]
        if missing:
            self.stdout.write(self.style.WARNING(
                f'以下文件夹未匹配到同名 SPU（跳过）：\n  ' + '\n  '.join(missing)
            ))

        concurrency = options['concurrency'] or max(1, (os.cpu_count() or 2) - 1)
        results = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_process_one_folder, name, os.path.join(root, name), spu_map, options['ratio']): name
                for name in folder_names if name in spu_map
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:  # noqa: BLE001
                    results.append({'folder': name, 'images': 0, 'videos': 0, 'errors': [str(e)]})

        total_img = sum(r['images'] for r in results)
        total_vid = sum(r['videos'] for r in results)
        failed = [r for r in results if r['errors']]
        self.stdout.write(self.style.SUCCESS(
            f'\n完成：处理 {len(results)} 个文件夹，共导入 {total_img} 张图片、{total_vid} 个视频。'
        ))
        for r in results:
            if r['errors']:
                self.stdout.write(self.style.ERROR(
                    f"  ✗ {r['folder']}: {r['images']}图/{r['videos']}视频 → {r['errors']}"
                ))
        if failed:
            raise CommandError(f'{len(failed)} 个文件夹导入存在错误，请查看上述日志')