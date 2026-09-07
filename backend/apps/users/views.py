import os
import re
from utils.storage import media_key

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.constants import Messages
from apps.users.email_service import EmailService, EmailVerifyService, EmailRateLimitError
from apps.users.serializers import (
    ChangePasswordSerializer,
    ChangeUsernameSerializer,
    ForgotPasswordResetSerializer,
    ForgotPasswordSendSerializer,
    LogoutSerializer,
    RegisterSerializer,
    SendEmailCodeSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    VerifyEmailCodeSerializer,
)
from apps.users.services import UserService
from utils.api_base_view import BaseApiView, PublicApiView
from apps.users.session_auth import set_auth_cookies

import logging
_logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """邮箱脱敏：a****b@example.com —— 用于前端提示「验证码已发送至 …」"""
    if not email or '@' not in email:
        return ''
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked_local = (local[:1] or '*') + '***'
    else:
        masked_local = f'{local[0]}***{local[-1]}'
    return f'{masked_local}@{domain}'


# ============================================================
# Admin 登录
# ============================================================

class AdminLoginRateThrottle(AnonRateThrottle):
    """后台登录频控（5/min），防密码爆破。"""
    scope = 'admin_login'


class AdminLoginView(PublicApiView):
    """管理员登录 —— 仅用用户名 + 密码。

    POST /api/admin/login/
    请求体: {username, password}

    需求调整：后台登录页只保留用户名 + 密码，去掉邮箱验证码 / Turnstile；
    管理员账号仍由 Django admin 创建（保留邮箱）。
    """
    throttle_classes = [AdminLoginRateThrottle]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Login success, returns JWT tokens'),
            400: OpenApiResponse(description='Invalid request'),
            401: OpenApiResponse(description='Invalid credentials'),
        }
    )
    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username:
            return Response({'detail': '用户名不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'detail': '密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth import get_user_model
        from apps.users.tokens import StampRefreshToken
        from apps.rbac.constants import Role
        from apps.rbac.services import has_role

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            _logger.warning('[AdminLogin] FAIL: no user for username=%r', username)
            return Response({'detail': '用户名不正确'}, status=status.HTTP_401_UNAUTHORIZED)

        # 后台访问资格：仅超管。组长/组员及运维（只读）角色均已被移除。
        if not has_role(user, Role.SUPERADMIN.value):
            _logger.warning('[AdminLogin] FAIL: no backend role for username=%r', username)
            return Response({'detail': '用户名不正确'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            _logger.warning('[AdminLogin] FAIL: password wrong for user=%r', username)
            return Response({'detail': '密码不正确'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = StampRefreshToken.for_user(user)
        response = Response({'authenticated': True})
        set_auth_cookies(response, refresh)
        return response


class AdminLoginCodeView(PublicApiView):
    """发送管理员登录邮箱验证码。"""
    """
    POST /api/admin/login/code/send/ —— 发送管理员登录邮箱验证码。

    请求体: {email}
    返回: {verify_id, expire_seconds}
    """

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Verification code sent, returns verify_id and expire_seconds'),
            400: OpenApiResponse(description='Invalid email'),
            500: OpenApiResponse(description='Send failed'),
        }
    )
    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {'detail': '邮箱不能为空'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 简单格式校验（re 已在文件顶部导入）
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return Response(
                {'detail': '邮箱格式不正确'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = EmailVerifyService.send_admin_verify_code(email)
            return Response(result, status=status.HTTP_200_OK)
        except EmailRateLimitError as e:
            return Response({'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            _logger.error('发送管理员登录验证码失败 email=%s error=%s', email, e)
            return Response(
                {'detail': '发送失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# 注册
# ============================================================

class RegisterView(PublicApiView):
    """用户注册（免邮箱验证码）。"""
    """
    POST /api/users/register/ —— 用户注册。

    需求调整：去掉邮箱验证码 / Turnstile，直接注册。
    入参: {username, password, email?, country_code?, phone?}
    """

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: RegisterSerializer,
            409: OpenApiResponse(description='Username/email/phone already exists'),
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            user = UserService.create_user(
                username=data['username'],
                password=data['password'],
                email=data.get('email') or '',
                country_code=data.get('country_code') or None,
                phone=data.get('phone') or None,
            )
        except ValueError as e:
            error_key = str(e)
            if error_key == 'USERNAME_EXISTS':
                return Response(
                    {'detail': Messages.USERNAME_EXISTS},
                    status=status.HTTP_409_CONFLICT,
                )
            if error_key == 'EMAIL_EXISTS':
                return Response(
                    {'detail': Messages.EMAIL_EXISTS},
                    status=status.HTTP_409_CONFLICT,
                )
            if error_key == 'PHONE_EXISTS':
                return Response(
                    {'detail': Messages.PHONE_EXISTS},
                    status=status.HTTP_409_CONFLICT,
                )
            raise

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# 登出
# ============================================================

class LogoutView(BaseApiView):
    """登出，将refresh token加入黑名单。"""
    """POST /api/users/logout/ —— 登出，将 refresh token 加入黑名单"""

    @extend_schema(
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description='Logout success')},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.logout(serializer.validated_data['refresh'])

        return Response(
            {'detail': Messages.LOGOUT_SUCCESS},
            status=status.HTTP_200_OK,
        )


# ============================================================
# 注销账号
# ============================================================

class DeactivateView(BaseApiView):
    """注销当前账号（软删除）。"""
    """POST /api/users/deactivate/ —— 注销当前账号（软删除）"""

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description='Account deactivated')},
    )
    def post(self, request):
        UserService.deactivate_user(request.user)

        return Response(
            {'detail': Messages.DEACTIVATE_SUCCESS},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Profile
# ============================================================

class UserProfileView(BaseApiView):
    """获取或更新当前用户扩展信息。"""
    """GET /api/users/profile/ —— 获取 / 更新当前用户的 Profile"""

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request):
        profile = UserService.get_or_create_profile(request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    @extend_schema(
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer}
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            profile = UserService.update_profile(request.user, **serializer.validated_data)
        except ValueError as e:
            if str(e) == 'PHONE_ALREADY_TAKEN':
                return Response(
                    {'detail': Messages.PHONE_ALREADY_TAKEN},
                    status=status.HTTP_409_CONFLICT,
                )
            raise

        result_serializer = UserProfileSerializer(profile)
        return Response(result_serializer.data)


# ============================================================
# 修改用户名
# ============================================================

class ChangeUsernameView(BaseApiView):
    """修改用户名（带30天冷却期）。"""
    """PUT /api/users/username/ —— 修改用户名（带冷却期）"""

    @extend_schema(
        request=ChangeUsernameSerializer,
        responses={
            200: OpenApiResponse(description='Username updated'),
            409: OpenApiResponse(description='Username already taken'),
            429: OpenApiResponse(description='Username change cooldown active'),
        }
    )
    def patch(self, request):
        serializer = ChangeUsernameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            UserService.change_username(
                request.user,
                serializer.validated_data['username'],
            )
        except ValueError as e:
            error_key = str(e)
            if error_key == 'USERNAME_ALREADY_TAKEN':
                return Response(
                    {'detail': Messages.USERNAME_ALREADY_TAKEN},
                    status=status.HTTP_409_CONFLICT,
                )
            if error_key == 'USERNAME_CHANGE_COOLDOWN':
                from django.conf import settings as s
                from datetime import timedelta
                from django.utils import timezone
                profile = UserService.get_or_create_profile(request.user)
                cfg = getattr(s, 'USERS_SETTINGS', {})
                days = cfg.get('USERNAME_CHANGE_COOLDOWN_DAYS', 30)
                next_date = (profile.username_changed_at + timedelta(days=days)).strftime('%Y-%m-%d')
                return Response(
                    {'detail': Messages.USERNAME_CHANGE_COOLDOWN.format(days=days, next_date=next_date)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            if error_key == 'SAME_USERNAME':
                return Response(
                    {'detail': 'New username is the same as current username.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        return Response(
            {'detail': Messages.PROFILE_UPDATED},
            status=status.HTTP_200_OK,
        )


class PasswordVerifyCodeSendView(BaseApiView):
    """修改密码二次确认 —— 向当前登录账号的注册邮箱发送验证码。

    POST /api/users/password/email-code/send/ —— 返回 verify_id（+ 脱敏邮箱）。

    安全要点：邮箱一律取 request.user.email，忽略请求体传入的任何 email，
    杜绝「用自己的邮箱收码、改别人的账号密码」。
    """

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Email code sent'),
            400: OpenApiResponse(description='Account has no email'),
            429: OpenApiResponse(description='Rate limit exceeded'),
            500: OpenApiResponse(description='Send failed'),
        }
    )
    def post(self, request):
        email = (request.user.email or '').strip()
        if not email:
            return Response({'detail': '账号未绑定邮箱，无法进行邮箱验证'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = EmailVerifyService.send_verify_code(email)
        except EmailRateLimitError as e:
            return Response({'detail': str(e), 'retry_after': e.retry_after}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            _logger.error('修改密码验证码发送失败 user=%s error=%s', request.user.pk, e)
            return Response({'detail': '发送失败，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        result['email_masked'] = _mask_email(email)
        return Response(result, status=status.HTTP_200_OK)


class ChangePasswordView(BaseApiView):
    """修改密码 —— 旧密码 + 邮箱验证码双重校验后设置新密码"""
    """POST /api/users/password/ —— Change account password"""

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password updated'),
            400: OpenApiResponse(description='Invalid old password / code / mismatch'),
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ── 邮箱验证码二次确认 ──
        verify_id = serializer.validated_data['verify_id']
        code = serializer.validated_data['code']

        # 校验验证码归属：必须是发给当前登录用户邮箱的码
        code_email = (EmailVerifyService.get_verify_email(verify_id) or '').strip().lower()
        if not code_email or code_email != (request.user.email or '').strip().lower():
            return Response(
                {'detail': '验证码无效或与当前账号邮箱不匹配，请重新获取'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # consume=False：先仅校验不销毁，改密成功后再显式消费。
        # 这样旧密码输错时验证码仍有效，用户不必因 60s 发码冷却而重等一轮；
        # 验证码本身仍有 10 分钟过期 + 每 verify_id 5 次试错上限的保护。
        if not EmailVerifyService.verify_code(verify_id, code, consume=False):
            return Response(
                {'detail': '验证码错误或已过期'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            UserService.change_password(
                request.user,
                serializer.validated_data['old_password'],
                serializer.validated_data['new_password'],
            )
        except ValueError as e:
            if str(e) == 'OLD_PASSWORD_INCORRECT':
                return Response(
                    {'detail': 'Old password is incorrect.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if str(e) == 'SAME_PASSWORD':
                return Response(
                    {'detail': 'New password must differ from the old one.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        # 改密成功 → 显式消费验证码，杜绝同一验证码被重放再次改密
        EmailVerifyService.consume_code(verify_id)

        # 安全戳旋转：密码变更使该用户所有旧会话立即失效，需重新登录
        from apps.users.tokens import rotate_user_stamp
        rotate_user_stamp(request.user.pk)

        return Response(
            {'detail': 'Password updated.'},
            status=status.HTTP_200_OK,
        )


# ============================================================
# 忘记密码 —— 发送验证码 + 重置为随机密码
# ============================================================

class ForgotPasswordSendView(PublicApiView):
    """忘记密码 —— 发送验证码到注册邮箱。

    POST /api/users/password/forgot/send/ —— 输入注册邮箱，发送6位验证码。

    安全：无论邮箱是否存在都返回成功（避免枚举已注册邮箱），
    但仅当邮箱存在时才真正发送邮件。
    """

    @extend_schema(
        request=ForgotPasswordSendSerializer,
        responses={
            200: OpenApiResponse(description='Verification code sent'),
            400: OpenApiResponse(description='Invalid email'),
            429: OpenApiResponse(description='Rate limit exceeded'),
        }
    )
    def post(self, request):
        serializer = ForgotPasswordSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].strip().lower()

        from django.contrib.auth import get_user_model
        User = get_user_model()

        # 邮箱不存在时也返回成功（防枚举），但不发送验证码
        if not User.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'If that email is registered, a verification code has been sent.'},
                status=status.HTTP_200_OK,
            )

        try:
            result = EmailVerifyService.send_verify_code(email)
        except EmailRateLimitError as e:
            return Response({'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            _logger.error('发送忘记密码验证码失败 email=%s error=%s', email, e)
            return Response({'detail': '发送失败，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)


class ForgotPasswordResetView(PublicApiView):
    """忘记密码 —— 校验验证码后重置为随机密码。

    POST /api/users/password/forgot/reset/ —— 校验验证码，生成10位随机密码并设置。

    成功 → 返回 { detail, new_password }，前端展示给用户，提示用新密码登录。
    """
    @extend_schema(
        request=ForgotPasswordResetSerializer,
        responses={
            200: OpenApiResponse(description='Password reset, returns new_password'),
            400: OpenApiResponse(description='Invalid or expired code'),
            404: OpenApiResponse(description='Email not found'),
        }
    )
    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_id = serializer.validated_data['verify_id']
        code = serializer.validated_data['code']

        # 校验验证码（一次性，成功后销毁）
        if not EmailVerifyService.verify_code(verify_id, code):
            return Response(
                {'detail': '验证码错误或已过期'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 从缓存取回发送验证码时的邮箱
        email = EmailVerifyService.get_verify_email(verify_id)
        if not email:
            return Response(
                {'detail': '验证码会话缺失，请重新发送验证码'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 找到对应用户
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {'detail': '该邮箱未注册'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 生成10位随机密码（含大小写字母与数字，满足密码强度校验）
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(10))

        # 设置新密码
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # 安全戳旋转：使该用户所有旧会话立即失效
        from apps.users.tokens import rotate_user_stamp
        rotate_user_stamp(user.pk)

        return Response(
            {
                'detail': 'Password has been reset.',
                'new_password': new_password,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# 邮箱验证码 —— 三阶段流程
# ============================================================

class SendEmailCodeView(PublicApiView):
    """发送邮箱验证码（需图片验证码）。"""
    """POST /api/users/email/send/ —— Phase 1: 发送邮箱验证码"""

    @extend_schema(
        request=SendEmailCodeSerializer,
        responses={
            200: OpenApiResponse(description='Email code sent'),
            429: OpenApiResponse(description='Rate limit exceeded'),
        }
    )
    def post(self, request):
        serializer = SendEmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = EmailService.send_code(serializer.validated_data['email'])

        if not result['success']:
            return Response(
                {'detail': result['message']},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response_data = {'detail': result['message']}
        if settings.DEBUG:
            _logger.info('DEBUG: 邮箱验证码 code=%s', result.get('code'))

        return Response(response_data)


class VerifyEmailCodeView(PublicApiView):
    """校验邮箱验证码，返回临时令牌。"""
    """
    POST /api/users/email/verify/ —— Phase 2: 校验验证码，签发临时令牌。

    成功 → 返回 verification_token（JWT, 5 分钟有效）
    失败 → 400
    """

    @extend_schema(
        request=VerifyEmailCodeSerializer,
        responses={
            200: OpenApiResponse(description='Email code verified, returns verification_token'),
            400: OpenApiResponse(description='Invalid code'),
        }
    )
    def post(self, request):
        serializer = VerifyEmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        is_valid = EmailService.verify_code(data['email'], data['code'])

        if not is_valid:
            return Response(
                {'detail': Messages.CODE_INVALID},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Phase 2 → 3: 签发临时令牌
        token = EmailService.issue_verification_token(data['email'])

        return Response({
            'detail': Messages.CODE_VERIFIED,
            'verification_token': token,
        })


# ============================================================
# 邮箱验证码发送与校验（独立验证码流程）
# ============================================================

class EmailVerifySendView(PublicApiView):
    """POST /api/users/email/verify/send/ — 发送邮箱验证码"""

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Email verification code sent'),
            400: OpenApiResponse(description='Invalid email'),
            500: OpenApiResponse(description='Send failed'),
        }
    )
    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'detail': '邮箱不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 简单格式校验
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return Response({'detail': '邮箱格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = EmailVerifyService.send_verify_code(email)
            return Response(result, status=status.HTTP_200_OK)
        except EmailRateLimitError as e:
            return Response({'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            _logger.error('发送邮箱验证码失败 email=%s error=%s', email, e)
            return Response({'detail': '发送失败，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailVerifyCheckView(PublicApiView):
    """POST /api/users/email/verify/check/ — 校验邮箱验证码"""

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description='Code verified'),
            400: OpenApiResponse(description='Invalid or expired code'),
        }
    )
    def post(self, request):
        verify_id = request.data.get('verify_id', '')
        code = request.data.get('code', '')
        if not verify_id or not code:
            return Response({'detail': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)

        if EmailVerifyService.verify_code(verify_id, code):
            return Response({'detail': '验证成功'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# 当前用户基本信息（供 Admin 前端使用）
# ============================================================

class UserMeView(BaseApiView):
    """GET /api/users/me/ —— 返回当前用户的基本信息（用于 Admin 认证）"""

    @extend_schema(responses={200: OpenApiResponse(description='List or retrieve')})
    def get(self, request):
        user = request.user
        group_member = getattr(user, 'admin_group_memberships', None)
        if group_member:
            group_member = group_member.filter(status=1).first()

        profile = user.profile if hasattr(user, 'profile') else None
        profile_data = UserProfileSerializer(profile).data if profile else None
        
        return Response({
            'id': user.id,
            'account_no': profile.account_no if profile else '',
            'username': user.username,
            'email': user.email,
            'phone': user.phone if hasattr(user, 'phone') else None,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'profile': profile_data,
            'is_group_leader': group_member.role == 'leader' if group_member else False,
            'is_group_member': group_member.role == 'member' if group_member else False,
            'group_name': group_member.group.name if group_member else None,
            'group_slug': group_member.group.slug if group_member else None,
        })

    @extend_schema(
        request=OpenApiResponse(description='{ nickname: string }'),
        responses={200: OpenApiResponse(description='Nickname updated')},
    )
    def patch(self, request):
        """PATCH /api/users/me/ —— 更新昵称等基本信息"""
        user = request.user
        nickname = request.data.get('nickname', '').strip()
        if nickname:
            if hasattr(user, 'profile') and user.profile:
                user.profile.nickname = nickname
                user.profile.save(update_fields=['nickname'])
            else:
                # 允许前端传 nickname 但后端无 profile 时静默忽略
                pass
        return Response({'detail': 'ok'})


# ============================================================
# 头像上传
# ============================================================

class AvatarUploadView(BaseApiView):
    """POST /api/users/upload-avatar/ —— 上传用户头像"""

    def post(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({'detail': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        from utils.upload_security import (
            UploadValidationError,
            to_webp,
            validate_image_upload,
        )
        try:
            ext, _mime = validate_image_upload(file, max_bytes=5 * 1024 * 1024)
        except UploadValidationError:
            return Response({'detail': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)

        # GIF 动画保留原格式（转 WebP 会丢帧）；其余统一转有损 WebP 后落盘
        webp_file = to_webp(file)
        _final_ext = (
            '.gif'
            if ext.lower() == '.gif'
            and getattr(webp_file, 'content_type', '') == 'image/gif'
            else '.webp'
        )
        filename = media_key('avatars', _final_ext)
        saved_path = default_storage.save(filename, webp_file)
        stored_url = default_storage.url(saved_path)
        # R2（S3）存储返回完整 CDN URL（https://cdn.carvenex.com/...），直接用；
        # 仅当返回相对路径（本地磁盘存储）时才补绝对 URL，避免 http(s):// 被二次包裹。
        full_url = stored_url if stored_url.startswith('http') else request.build_absolute_uri(stored_url)

        user = request.user
        if hasattr(user, 'profile') and user.profile:
            user.profile.avatar = full_url
            user.profile.save(update_fields=['avatar'])
        elif hasattr(user, 'profile'):
            # 惰性创建 profile（老用户可能没有）
            from apps.users.models import UserProfile
            UserProfile.objects.create(user=user, avatar=full_url)

        return Response({'avatar_url': full_url})


class AdminEmailVerifyView(PublicApiView):
    """公开邮箱验证端点（无需登录）。

    POST /api/users/email/admin-verify/  {token}
    解码欢迎邮件中的 JWT 令牌（type=admin_email_verify），将对应账号的
    email_verified 置为 True，返回 200 {verified:true, email}。
    令牌无效/过期 → 400 {detail, code:'TOKEN_INVALID'}。
    """

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response(
                {'detail': '缺少验证令牌', 'code': 'TOKEN_INVALID'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = EmailService.decode_admin_email_verify_token(token)
        except ValueError as e:
            return Response(
                {'detail': str(e), 'code': 'TOKEN_INVALID'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (payload.get('email') or '').lower()
        if not email:
            return Response(
                {'detail': '令牌缺少邮箱信息', 'code': 'TOKEN_INVALID'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        from apps.users.models import UserProfile

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {'detail': '账号不存在', 'code': 'TOKEN_INVALID'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        # 幂等：已验证直接返回成功
        if profile.email_verified:
            return Response({'verified': True, 'email': user.email})

        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        return Response({'verified': True, 'email': user.email})
