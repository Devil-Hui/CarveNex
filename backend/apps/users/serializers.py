from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import UserProfile, validate_country_code, validate_phone
from apps.users.email_service import EmailService
from apps.users.validators import validate_username, validate_email, validate_password

User = get_user_model()
_cfg = getattr(settings, 'USERS_SETTINGS', {})


# ============================================================
# 注册
# ============================================================

class RegisterSerializer(serializers.Serializer):
    """
    用户注册 —— 免邮箱验证码（需求调整：去掉邮箱验证 / Turnstile）。

    注册只需：用户名 / 密码 / 可选邮箱 / 可选手机。不再强制邮箱验证，
    用户可直接创建账号。
    """
    username = serializers.CharField(
        required=True,
        validators=[validate_username],
        help_text='Username, 4-32 chars: letters, digits, _ or -.',
    )
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        help_text='Password, ≥8 chars with uppercase, lowercase, and digit/special char.',
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default='',
        help_text='Email (optional).',
    )
    country_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10,
        help_text='Country calling code, e.g. +86.',
    )
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text='Phone number without country code.',
    )

    def validate_username(self, value):
        return validate_username(value)

    def validate_password(self, value):
        return validate_password(value)

    def validate_country_code(self, value):
        if value:
            validate_country_code(value)
        return value

    def validate_phone(self, value):
        value = value.strip() if value else ''
        if value:
            validate_phone(value)
        return value

    def validate(self, data):
        """跨字段校验：email 归一化，无邮箱则允许注册（非必填）"""
        data['email'] = (data.get('email') or '').strip().lower()
        # 保留 phone/country_code 原样
        return data


# ============================================================
# 登录 —— 由 SimpleJWT TokenObtainPairView 处理，此处不自定义
# ============================================================


# ============================================================
# 登出
# ============================================================

class LogoutSerializer(serializers.Serializer):
    """登出 —— 需要 refresh token 以加入黑名单"""
    refresh = serializers.CharField(
        help_text='Refresh token to blacklist.',
    )


# ============================================================
# Profile
# ============================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """用户扩展信息（只读）"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_phone = serializers.CharField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'country_code', 'phone',
            'full_phone', 'avatar', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """更新区号 / 手机号"""

    class Meta:
        model = UserProfile
        fields = ['country_code', 'phone']

    def validate_country_code(self, value):
        if value:
            validate_country_code(value)
        return value

    def validate_phone(self, value):
        value = value.strip() if value else ''
        if value:
            validate_phone(value)
        return value


# ============================================================
# 修改用户名
# ============================================================

class ChangeUsernameSerializer(serializers.Serializer):
    """修改用户名 —— 格式校验；唯一性由 service 层处理"""
    username = serializers.CharField(
        min_length=_cfg.get('USERNAME_MIN_LENGTH', 3),
        max_length=_cfg.get('USERNAME_MAX_LENGTH', 15),
        help_text='New username, 3-15 characters.',
    )

    def validate_username(self, value):
        # 格式校验在此；唯一性由 service 层返回 409
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码 —— 旧密码 + 邮箱验证码双重校验，新密码需确认

    安全设计：仅凭旧密码不足以改密（会话劫持/共用电脑场景），
    必须叠加一次「邮箱验证码」二次确认（verify_id + code）。
    验证码归属邮箱由视图层强制比对 request.user.email，
    避免攻击者拿自己邮箱的 verify_id 改他人密码。
    """
    old_password = serializers.CharField(write_only=True, help_text='Current password.')
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        help_text='New password, 8-128 chars.',
    )
    confirm_password = serializers.CharField(write_only=True, help_text='Repeat new password.')
    verify_id = serializers.CharField(write_only=True, help_text='verify_id from the email code send step.')
    code = serializers.CharField(
        write_only=True,
        min_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
        max_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
        help_text='6-digit code sent to the account email.',
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次输入的新密码不一致'})
        return attrs


class ForgotPasswordSendSerializer(serializers.Serializer):
    """忘记密码 —— 发送验证码到注册邮箱"""
    email = serializers.EmailField(help_text='Registered email address.')


class ForgotPasswordResetSerializer(serializers.Serializer):
    """忘记密码 —— 校验验证码后重置为随机密码"""
    verify_id = serializers.CharField(help_text='verify_id returned by send step.')
    code = serializers.CharField(
        min_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
        max_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
        help_text='6-digit code from email.',
    )



# ============================================================
# 邮箱验证码
# ============================================================

class SendEmailCodeSerializer(serializers.Serializer):
    """发送邮箱验证码（已移除图片验证码——旧版本残余，服务端现直接校验邮箱格式后发码）"""
    email = serializers.EmailField(help_text='Email address.')


class VerifyEmailCodeSerializer(serializers.Serializer):
    """校验邮箱验证码"""
    email = serializers.EmailField()
    code = serializers.CharField(
        min_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
        max_length=_cfg.get('VERIFICATION_CODE_LENGTH', 6),
    )
