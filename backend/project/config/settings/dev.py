from .base import *  # 继承 base.py

DEBUG = True

# ⚠️ 开发环境跳过 SSL 证书验证，SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE 使用默认值 False
EMAIL_BACKEND = 'utils.smtp_backend.DevEmailBackend'

ALLOWED_HOSTS = [
    '127.0.0.1',
    '172.20.10.2',
    'localhost',
    'testserver',
    'web',
    'django-app',
    'host.docker.internal',
    # 本机即生产源站：允许 Cloudflare Tunnel 公网域名访问
    'api.carvenex.com',
    'carvenex.com',
    'www.carvenex.com',
    '.trycloudflare.com',
]
ALLOWED_HOSTS.extend(
    host.strip()
    for host in os.getenv('DJANGO_DEV_ALLOWED_HOSTS', '').split(',')
    if host.strip()
)

# ============================================================
# CORS / CSRF —— 本机即生产源站时需支持公网跨子域访问
# （docker-compose.yml 用 DJANGO_ENV=dev，但通过 Cloudflare Tunnel 暴露公网，
#  base.py 的 CORS_ALLOWED_ORIGINS 仅含 localhost，浏览器跨域 POST 会被拦截）
# ============================================================

# CORS：优先从环境变量读取（.env 的 CORS_ORIGINS），未配置时回退本地开发默认值
_cors_env = os.getenv('CORS_ORIGINS', '')
if _cors_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
    ]
# 允许跨域携带 Cookie（axios withCredentials: true 需要此配置）
CORS_ALLOW_CREDENTIALS = True

# CSRF 跨域信任：admin/www/shop → api 子域的 POST 请求需要
# 开发环境（http 源）也必须纳入，否则本地用 Vite(12700) 经代理打后端时
# Origin 检查可能因 Host 不一致而 403。信任全部 CORS 源 + 前端开发源。
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS) + [
    'http://localhost:12700',
    'http://127.0.0.1:12700',
]

# 跨子域 Cookie：公网域名场景下 csrftoken/sessionid 落在父域 .carvenex.com，
# 使 admin/www/shop 前端能从 document.cookie 读取 csrftoken 并随 axios 写请求回传
# （否则 host-only cookie 仅 api.carvenex.com 可读，前端域拿不到 → X-CSRFToken 头缺失 → 403）
# 本地 localhost 开发：在 .env 设 COOKIE_DOMAIN=（空）→ 使用 host-only cookie，
# 浏览器才能在 localhost 上存储并回传 CSRF/鉴权 cookie（跨域 .carvenex.com cookie 会被拒绝）。
_COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', '.carvenex.com' if '.carvenex.com' in (os.getenv('DOMAIN', '') or '') else '')
if _COOKIE_DOMAIN:
    CSRF_COOKIE_DOMAIN = _COOKIE_DOMAIN
    SESSION_COOKIE_DOMAIN = _COOKIE_DOMAIN
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'
    # nginx-tunnel 已设 X-Forwarded-Proto: https，信任该头以正确识别 HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timezone.timedelta(minutes=15),  # 本地开发：访问令牌 15 分钟（与线上一致，避免超长cookie）
    'REFRESH_TOKEN_LIFETIME': timezone.timedelta(hours=2),  # 本地开发：刷新令牌 2 小时（原 9999 天≈27 年，已修正）
    'ROTATE_REFRESH_TOKENS': False,  # 开发环境不轮换刷新令牌，避免并发竞态导致黑名单（故 dev 为严格 2h 会话，prod 为空闲续期）
    'BLACKLIST_AFTER_ROTATION': False,  # 开发环境禁用黑名单，防止页面刷新后 token 丢失
    'UPDATE_LAST_LOGIN': True,  # 更新用户最后登录时间
    'ALGORITHM': 'HS256',  # 使用的加密算法
    'SIGNING_KEY': SECRET_KEY,  # 签名密钥，使用Django的SECRET_KEY
    'VERIFYING_KEY': None,  # 验证密钥，使用对称加密时为None
    'AUTH_HEADER_TYPES': ('Bearer',),  # 认证头类型
    'AUTH_HEADER_NAME': 'Authorization',  # 认证头名称
    'USER_ID_FIELD': 'id',  # 用户模型中用作用户ID的字段
    'USER_ID_CLAIM': 'user_id',  # token中用户ID的声明名称
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',  # JWT ID声明，用于防止重放攻击
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timezone.timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timezone.timedelta(days=1),
}

# 文件存储配置
FILE_STORAGE = os.getenv('FILE_STORAGE', 'local')  # 可选 'local' 或 'r2'
MEDIA_PATH = os.getenv('MEDIA_PATH', 'media') or 'media'
MEDIA_URL = f"/{MEDIA_PATH.strip('/')}/"
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_PATH)
# 上传临时目录指向 media 数据卷（见 base.resolve_upload_temp_dir 注释：
# 生产 /tmp 只有 32MB tmpfs，并发四尺寸上传会 ENOSPC）
FILE_UPLOAD_TEMP_DIR = resolve_upload_temp_dir(MEDIA_ROOT) or None
FILE_STORAGE_MAX_SIZE = int(os.getenv('FILE_STORAGE_MAX_SIZE', '5'))  # 5MB
FILE_STORAGE_ALLOWED_TYPES = os.getenv('FILE_STORAGE_ALLOWED_TYPES', "image/jpeg,image/png,image/webp").split(',')

# ── R2 对象存储（凭据齐全时启用；上传失败自动回退数据库，见 utils.storage）──
# Cloudflare R2 (fill in after creating R2 bucket)
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '')
R2_BUCKET = os.getenv('R2_BUCKET', '')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '')  # e.g. https://cdn.carvenex.com

# 本地应急磁盘回退：未显式配置 LOCAL_FALLBACK_ROOT 时，默认落到 MEDIA_ROOT/pic，
# 便于 R2 在本机不可达时读取回退到已同步的 pic/ 目录副本（见 utils.storage.R2DBFallbackStorage）。
if not os.getenv('LOCAL_FALLBACK_ROOT'):
    LOCAL_FALLBACK_ROOT = os.path.join(MEDIA_ROOT, 'pic')
R2_FALLBACK_ENABLED = os.getenv('R2_FALLBACK_ENABLED', 'true').lower() == 'true'

# dev 默认用本地存储（图片存本地磁盘、/media/ 直接 serve），
# 这样开发时在「无 R2/CND 访问环境」下图片也能正常显示。
# 仅当显式 env DEV_R2_STORAGE=1 时才切换 R2 端到端验证。
if os.getenv('DEV_R2_STORAGE', '').lower() in ('1', 'true', 'yes') \
        and R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET:
    # 带「S3→R2」回退的后端：断网/S2/R2 不可达时自动落库 MediaBlob（上传/展示回退）
    STORAGES['default']['BACKEND'] = 'utils.storage.R2DBFallbackStorage'
    AWS_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET
    AWS_S3_ENDPOINT_URL = f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_FILE_OVERWRITE = True
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = None
    if R2_PUBLIC_URL:
        # 开发调试环境：不上 R2/CDN 覆盖 MEDIA_URL，保持本地相对 `/media/`，
        # 前端 resolveMediaUrl('/media/...') → 后端 apiOrigin + '/media/...'（本地磁盘兜底，
        # DEBUG 下 urls.py 已把 MEDIA_ROOT serve 到 /media/），确保本地图片正常显示。
        # 生产(prod.py)才使用 CDN 域名作为对外图床。
        AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_URL.replace('https://', '').replace('http://', '').rstrip('/')
