"""
（已废弃）把商品审核组成员身份同步为 RBAC 全局角色。

需求调整：已删除管理组组长 / 组员角色（admin_leader / admin_member），
管理操作统一由超管承担。本命令不再同步任何角色，仅返回提示以免误用。
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '（已废弃）管理组组长/组员角色已删除，无需同步'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='只报告将要写入的内容，不落库'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                'sync_admin_group_roles 已废弃：组长/组员角色（admin_leader / admin_member）'
                '已从系统移除，管理操作统一由超管承担，无需同步 RBAC 角色。'
            )
        )