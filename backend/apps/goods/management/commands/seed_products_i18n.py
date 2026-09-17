"""
补全品牌商品三语字段（幂等 + 静态快照，保证 docker 更新/新机器数据一致）

为 seed_products 导入的 56 个商品补齐 name/description 的中文与阿拉伯语版本：
- name / description         -> 中文（默认语言，前端 zh-CN 界面使用）
- name_ar / description_ar   -> 阿拉伯语

数据盲点：seed_products 的 xlsx 只提供了英文标题与英文描述，导入时把英文写进了
name/name_en 与 description/description_en，name_ar/description_ar 为空。

本命令的翻译来源（按优先级）：
  1) 静态快照 seed_products/i18n_zh_ar.json（以 name_en 为 key）
     —— 由 --dump 用“当前已验证库”导出，随 seed_products/ 一起被带到新机器；
        读取命中时直接用快照里的译文，100% 与验证库一致，且**离线可用、不依赖腾讯 TMT**。
  2) TMT 机器翻译（腾讯云） —— 仅当快照缺失时才调用，作为兜底。

幂等设计：
- 已存在对应字段数值时认为已翻译，跳过（避免重复覆盖/扣费）。
- 翻译失败（未配置密钥 / 接口异常）发出 WARNING，不阻断其它商品。

用法：
    python manage.py seed_products_i18n             # 补全全部缺失字段（静态优先，缺失走 TMT）
    python manage.py seed_products_i18n --dry-run   # 只打印将处理哪些 SPU
    python manage.py seed_products_i18n --dump      # 把当前库已翻译的三语导出为静态快照 JSON

    注意：--dump 应该在“翻译好且校验过”的库上运行一次，这样快照就是权威译文，
          之后新机器重建只要 seed_products_i18n 就能 100% 复刻，与当前库完全一致。
"""
import json
import os

from django.core.management.base import BaseCommand

from apps.goods.models import SPU

# 默认静态快照路径（相对 backend/ 工作目录，与 seed_products/ 同级；会随代码/seed_products 部署到新机器）
DEFAULT_SNAPSHOT = os.path.normpath('seed_products/i18n_zh_ar.json')


class Command(BaseCommand):
    help = '补全商品三语字段（中文+阿语），静态快照优先，缺失走腾讯 TMT'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='只打印计划，不读 TMT/不写库')
        parser.add_argument('--dump', action='store_true',
                            help='把当前库已翻译的三语导出为静态快照（在验证过的库上执行）')
        parser.add_argument('--snapshot', type=str, default=DEFAULT_SNAPSHOT,
                            help='静态快照路径（默认 seed_products/i18n_zh_ar.json）')
        parser.add_argument('--fields', type=str, default='all',
                            help='只翻译指定字段，逗号分隔：name,description')

    def handle(self, *args, **options):
        dry = options['dry_run']
        snapshot_path = options['snapshot']

        if options['dump']:
            self._dump_snapshot(snapshot_path)
            return

        fields = {f.strip() for f in options['fields'].split(',') if f.strip()}
        if fields != {'all'}:
            want = set()
            if 'name' in fields:
                want |= {'name', 'name_ar'}
            if 'description' in fields:
                want |= {'description', 'description_ar'}
            fields = want
        else:
            fields = {'name', 'description', 'name_ar', 'description_ar'}

        from apps.goods.translation_service import translate_text

        # 读静态快照（若存在）
        snapshot = self._load_snapshot(snapshot_path)
        if snapshot:
            self.stdout.write(self.style.SUCCESS(
                f'使用静态快照 {snapshot_path} 作为翻译来源（{len(snapshot)} 个商品）'))

        spus = SPU.objects.filter(deleted_at__isnull=True).order_by('id')
        self.stdout.write(f'共 {spus.count()} 个商品，需要翻译字段: {sorted(fields)}')

        done = skipped = failed = 0
        for spu in spus:
            spu_done = False
            key = spu.name_en or spu.name or ''
            entry = (snapshot or {}).get(key) or {}

            # ── 中文（name/description） ──
            # seed_products 把英文标题写进了 name，需在『当前是英文/非中文』时用中文覆盖。
            if 'name' in fields and not self._is_cn(spu.name):
                zh_name = entry.get('name') or self._tr(translate_text, spu.name_en or spu.name, 'en', 'zh', dry)
                if zh_name:
                    spu.name = zh_name; spu_done = True
                else:
                    failed += 1; self.stdout.write(self.style.WARNING(f'  [!] {spu.id} name 缺失'))
            if 'description' in fields and not self._is_cn(spu.description):
                zh_desc = entry.get('description') or self._tr(
                    translate_text, spu.description_en or '', 'en', 'zh', dry)
                if zh_desc:
                    spu.description = zh_desc; spu_done = True
                else:
                    failed += 1
            # ── 阿拉伯语 ──
            if 'name_ar' in fields and not (spu.name_ar or '').strip():
                ar_name = entry.get('name_ar') or self._tr(
                    translate_text, spu.name_en or spu.name, 'en', 'ar', dry)
                if ar_name:
                    spu.name_ar = ar_name; spu_done = True
                else:
                    failed += 1
            if 'description_ar' in fields and not (spu.description_ar or '').strip():
                ar_desc = entry.get('description_ar') or self._tr(
                    translate_text, spu.description_en or spu.description, 'en', 'ar', dry)
                if ar_desc:
                    spu.description_ar = ar_desc; spu_done = True
                else:
                    failed += 1

            if spu_done:
                if dry:
                    self.stdout.write(f'  [DRY] 将补齐: {(spu.name_en or "")[:50]}')
                    done += 1
                    continue
                spu.save(update_fields=[f for f in
                                        ('name', 'description', 'name_ar', 'description_ar')
                                        if f in ('name', 'description', 'name_ar', 'description_ar') and getattr(spu, f)])
                done += 1
                self.stdout.write(f'  + {(spu.name_en or "")[:50]}')
            else:
                skipped += 1

        if not dry:
            self.stdout.write(self.style.SUCCESS(f'完成: 更新 {done}, 已跳过 {skipped}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'预览: 将更新 {done}, 跳过 {skipped}'))

    # ---------- 静态快照 ----------
    def _load_snapshot(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _dump_snapshot(self, path):
        """把当前库的商品三语导出为静态快照（以 name_en 为 key）。"""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        data = {}
        for spu in SPU.objects.filter(deleted_at__isnull=True).order_by('id'):
            key = spu.name_en or spu.name or str(spu.id)
            data[key] = {
                'name': spu.name or '',
                'name_ar': spu.name_ar or '',
                'description': spu.description or '',
                'description_ar': spu.description_ar or '',
            }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.stdout.write(self.style.SUCCESS(
            f'已导出 {len(data)} 个商品的三语快照 -> {os.path.normpath(path)}'))

    def _tr(self, translate_text, text, src, target, dry):
        if dry:
            return '【DRY】'
        text = (text or '').strip()
        if not text:
            return ''
        try:
            return translate_text(text, source=src, target=target) or ''
        except Exception:  # noqa: BLE001
            return ''

    @staticmethod
    def _is_cn(text):
        """粗略判断文本是否已是中文（含 CJK 统一表意文字）。"""
        import re
        return bool(re.search(r'[\u4e00-\u9fff]', (text or '') or ''))