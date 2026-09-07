from django.urls import path

from apps.users.admin_views import (
    AdminUserListView,
    AdminUserRoleView,
)

urlpatterns = [
    # 按 account_no / role 检索（不暴露内部 id）
    path('', AdminUserListView.as_view(), name='admin-user-list'),
    # 按 account_no 指派可指派角色
    path('<str:account_no>/roles', AdminUserRoleView.as_view(), name='admin-user-roles'),
]
