import logging
from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import exceptions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model

from apps.users.tokens import (
    STAMP_CLAIM,
    StampRefreshToken,
    StampTokenObtainPairSerializer,
    get_db_stamp,
)
from utils.api_jwt_authentication import UsersJWTAuthentication
from utils.exceptions import (
    AuthException,
    ErrorCodes,
)


ACCESS_COOKIE = 'carvenex_access'
REFRESH_COOKIE = 'carvenex_refresh'

logger = logging.getLogger(__name__)


def _cookie_kwargs():
    kwargs = {
        'httponly': True,
        'secure': settings.SESSION_COOKIE_SECURE,
        'samesite': settings.SESSION_COOKIE_SAMESITE,
        'path': '/',
    }
    # 与 csrftoken 保持一致，落到父域 .carvenex.com，跨子域（admin/www/shop → api）自动携带
    domain = getattr(settings, 'CSRF_COOKIE_DOMAIN', None)
    if domain:
        kwargs['domain'] = domain
    return kwargs


def set_auth_cookies(response, refresh):
    response.set_cookie(
        ACCESS_COOKIE,
        str(refresh.access_token),
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **_cookie_kwargs(),
    )
    response.set_cookie(
        REFRESH_COOKIE,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        **_cookie_kwargs(),
    )


def clear_auth_cookies(response):
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        kwargs = {'path': '/', 'samesite': settings.SESSION_COOKIE_SAMESITE}
        domain = getattr(settings, 'CSRF_COOKIE_DOMAIN', None)
        if domain:
            kwargs['domain'] = domain
        response.delete_cookie(name, **kwargs)


class CookieJWTAuthentication(UsersJWTAuthentication):
    """Authenticate browser requests from HttpOnly cookies with CSRF checks."""

    def authenticate(self, request):
        if self.get_header(request) is not None:
            return None
        raw_token = request.COOKIES.get(ACCESS_COOKIE)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        SessionAuthentication().enforce_csrf(request)
        return self.get_user(validated_token), validated_token


class CSRFCookieView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        get_token(request)
        return Response({'csrf_ready': True}, status=status.HTTP_200_OK)


class AdminLoginRateThrottle(AnonRateThrottle):
    """后台/商城登录频控：防密码爆破。独立 scope（admin_login，5/min）。"""
    scope = 'admin_login'


class BrowserLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AdminLoginRateThrottle]

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        # 需求调整：去掉人机验证 —— 登录百分百放行（不再校验 turnstile_token）。
        # 前端即使仍传 token 也不校验，避免任何环境（不含 Turnstile 配置/离线）导致登录被卡。

        raw_login = request.data.get('username', '')
        password = request.data.get('password', '')
        # 支持邮箱登录：输入含 @ 时按 email 解析真实 username（占位符标注为 Email）
        login_id = raw_login
        if '@' in login_id:
            from django.contrib.auth import get_user_model
            U = get_user_model()
            user = U.objects.filter(email__iexact=login_id).only('username').first()
            if user:
                login_id = user.username
        serializer = StampTokenObtainPairSerializer(data={
            'username': login_id,
            'password': password,
        })
        serializer.is_valid(raise_exception=True)
        refresh = StampRefreshToken(serializer.validated_data['refresh'])
        response = Response({'authenticated': True})
        set_auth_cookies(response, refresh)
        return response


class BrowserRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not raw_refresh:
            raise exceptions.AuthenticationFailed('Refresh cookie is missing.')
        try:
            refresh = StampRefreshToken(raw_refresh)
        except TokenError:
            # 无效/过期 refresh token 返回 401（前端引导重新登录），而非 500
            raise exceptions.AuthenticationFailed('Refresh token is invalid or expired.')
        # 安全戳校验：角色/密码变更后旧 refresh 令牌的 stamp 与 DB 不一致 → 强制重新登录
        token_stamp = refresh.payload.get(STAMP_CLAIM)
        if token_stamp is not None:
            uid = refresh.payload.get('user_id')
            if uid:
                User = get_user_model()
                user = User.objects.filter(id=uid, is_active=True).select_related('profile').first()
                if user is None or get_db_stamp(user) != token_stamp:
                    raise AuthException(ErrorCodes.REAUTH_REQUIRED)
        response = Response({'authenticated': True})
        set_auth_cookies(response, refresh)
        return response


class BrowserLogoutView(APIView):
    # 登出必须在任意状态都能完成（即使 access token 已过期/缺失），否则用户将
    # 被困在“无法登出”的状态。因此不依赖 CookieJWTAuthentication 认证成功，
    # 仅做 CSRF 校验后清除 cookie，并尽力把 refresh token 加入黑名单。
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except Exception as e:  # noqa: BLE001
                # token 已轮换/无效/已入黑名单等均不影响登出成功，绝不能抛错导致 500
                logger.warning('登出黑名单 refresh token 失败: %s', e, exc_info=True)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response
