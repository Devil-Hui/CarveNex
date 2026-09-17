from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, AllowAny
from django.conf import settings
from utils.api_permission import ApiPermission
from utils.api_jwt_authentication import UsersJWTAuthentication
from apps.users.session_auth import CookieJWTAuthentication
from utils.api_base_pagination import BasePagination, AdminPagination
from utils.admin_authentication import ExpiringTokenAuthentication
import logging

logger = logging.getLogger('biz')


class PublicApiView(APIView):
    """公开接口基类：无需认证，允许匿名访问。

    公开展示页接口（首页/落地页/前台广告位等）一律不走限流——原因：
    1) 这些接口返回的是公开数据，无敏感写操作；
    2) 前端 SPA 单页面打开即触发十几个并发请求，全局 anon throttle 极易误命中；
    3) DoS 防护由网关/Vite 代理/前端缓存层负责，应用层保持轻量。
    真正需要限流的子集（搜索、支付等）请在子视图显式声明 throttle_classes。
    """
    authentication_classes = [CookieJWTAuthentication, UsersJWTAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = ()
    pagination_class = BasePagination

    def paginate_queryset(self, queryset):
        self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


class BaseApiView(APIView):
    """
    用户端基础视图基类。
    
    ⚠️ 安全说明:
    默认 permission_classes = [ApiPermission] 仅检查 user.is_active，
    不检查 staff/superuser 角色。新增视图若包含敏感操作，必须
    显式覆盖 permission_classes 以添加更严格的权限检查。
    
    所有 Admin 视图应使用 AdminApiView 或显式设置 IsAdminUser 类权限。
    """
    authentication_classes = [CookieJWTAuthentication, UsersJWTAuthentication]
    permission_classes = [ApiPermission]
    pagination_class = BasePagination

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 运行时守卫：检测新子类的默认权限是否未覆盖
        # 警告：此检测在模块导入时触发，不拦截请求
        if 'permission_classes' not in cls.__dict__ and settings.DEBUG:
            logger.debug(
                f'BaseApiView 子类 {cls.__name__} 未覆盖 permission_classes，'
                f'使用默认值 {cls.permission_classes}（仅检查 is_active）'
            )

    def paginate_queryset(self, queryset):
        self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


class AdminApiView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = AdminPagination

    def paginate_queryset(self, queryset):
        self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
