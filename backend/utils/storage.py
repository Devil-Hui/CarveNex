"""文件存储工具类 —— 工厂模式 (Local / Cloudflare R2)

Usage:
    from utils.storage import get_storage

    storage = get_storage()
    result = storage.upload(file_name, file_content, content_type='image/jpeg')
    url = storage.get_url(file_name)
    storage.delete(file_name)
"""

import logging
import os
import time as _time
import traceback
import uuid as _uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# ==================== 统一对象存储 key 规范 ====================

def media_key(prefix: str, ext: str, *, now: "datetime | None" = None) -> str:
    """生成大厂规范的对象存储 key：{prefix}/{YYYY}/{MM}/{DD}/{uuid}.{ext}。

    按上传日期分区，便于生命周期管理、列举与灾备；不含顶层 media/ 段——
    R2 模式 URL 由自定义域名直接拼 key（https://cdn.carvenex.com/<key>），
    local 模式由 MEDIA_URL(/media/) 拼接，两种模式都正确，勿再手动加 media/。

    prefix 例：'products' / 'uploads' / 'avatars' / 'support' /
    'chat/images' / 'chat/videos'；允许带首尾斜杠，自动规整。
    ext 可带或不带点，空则不加后缀。now 注入用于测试。
    """
    now = now or datetime.now(timezone.utc)
    prefix = prefix.strip('/')
    ext = ext if ext.startswith('.') else (f'.{ext}' if ext else '')
    return f"{prefix}/{now:%Y}/{now:%m}/{now:%d}/{_uuid.uuid4().hex}{ext}"


# ==================== 数据库回退存储 ====================
# 断网 / R2 不可达时，把文件字节落库（apps.media.MediaBlob），读取时经统一
# /api/media/db/<key> 端点回传。DB 永远可用，保证无外网也能上传与展示。

DB_MEDIA_PREFIX = '/api/media/db/'


def db_media_url(file_name: str) -> str:
    """数据库回退媒体的访问 URL（本地自有域名，由 Django 视图读库回传）。"""
    from urllib.parse import quote
    return f'{DB_MEDIA_PREFIX}{quote(file_name, safe="/-._")}'


# ==================== 抽象基类 ====================

class BaseStorage(ABC):
    """存储后端抽象基类"""

    def __init__(self):
        self.max_file_size = int(getattr(settings, 'FILE_STORAGE_MAX_SIZE', 10)) * 1024 * 1024

    def check_file_size(self, size: int):
        if size > self.max_file_size:
            raise ValueError(f'文件大小超过 {self.max_file_size // 1024 // 1024}MB 限制')

    def check_file_type(self, content_type: str):
        allowed = getattr(settings, 'FILE_STORAGE_ALLOWED_TYPES', [])
        if allowed and content_type not in allowed:
            raise ValueError(f'不支持的文件类型: {content_type}')

    @abstractmethod
    def upload(self, file_name: str, file_content: bytes, content_type: str = None) -> dict:
        """上传文件，返回 {'url': str, 'message': str}"""
        ...

    @abstractmethod
    def delete(self, file_name: str) -> bool:
        """删除文件，返回是否成功"""
        ...

    @abstractmethod
    def get_url(self, file_name: str) -> str:
        """获取文件访问 URL"""
        ...


# ==================== Cloudflare R2 ====================

class R2Storage(BaseStorage):
    """Cloudflare R2 (S3 兼容)"""

    def __init__(self):
        super().__init__()
        import boto3

        account_id = getattr(settings, 'R2_ACCOUNT_ID', '')
        access_key = getattr(settings, 'R2_ACCESS_KEY_ID', '')
        secret_key = getattr(settings, 'R2_SECRET_ACCESS_KEY', '')
        self.bucket_name = getattr(settings, 'R2_BUCKET', '')

        endpoint = f'https://{account_id}.r2.cloudflarestorage.com'
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.base_url = getattr(settings, 'R2_PUBLIC_URL', f'{endpoint}/{self.bucket_name}')

    def upload(self, file_name: str, file_content: bytes, content_type: str = None) -> dict:
        try:
            self.check_file_size(len(file_content))
            if content_type:
                self.check_file_type(content_type)

            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                **extra_args,
            )
            url = f'{self.base_url}/{file_name}'
            return {'url': url, 'message': '上传成功'}
        except Exception as e:
            # 断网 / R2 不可达：回退到数据库存储，保证离线仍可上传与展示。
            logger.warning('R2 上传失败，回退数据库存储: %s\n%s', file_name, e)
            return DBStorage().upload(file_name, file_content, content_type)

    def delete(self, file_name: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=file_name)
            return True
        except Exception as e:
            logger.error(f'R2 删除失败: {file_name}: {e}')
            return False

    def get_url(self, file_name: str) -> str:
        return f'{self.base_url}/{file_name}'

    def read(self, file_name: str):
        """从 R2 读取对象字节，返回 (bytes, content_type)；不存在/不可达返回 (None, None)。"""
        try:
            obj = self.client.get_object(Bucket=self.bucket_name, Key=file_name)
            body = obj.get('Body')
            data = body.read() if body is not None else b''
            ctype = obj.get('ContentType') or 'application/octet-stream'
            return data, ctype
        except Exception as e:
            logger.warning('R2 读取失败: %s | %s', file_name, e)
            return None, None


# ==================== 数据库回退存储 ====================

class DBStorage(BaseStorage):
    """数据库存储（离线兜底）：文件字节落库，读取由 /api/media/db/<key> 视图回传。"""

    def _save(self, file_name: str, file_content: bytes, content_type: str):
        # 延迟导入，避免启动期循环依赖（media 模型需 Django apps 就绪）
        from apps.media.models import MediaBlob
        MediaBlob.objects.update_or_create(
            key=file_name,
            defaults={
                'content': file_content,
                'content_type': content_type or '',
                'size': len(file_content),
            },
        )

    def upload(self, file_name: str, file_content: bytes, content_type: str = None) -> dict:
        try:
            self.check_file_size(len(file_content))
            self._save(file_name, file_content, content_type)
            return {'url': db_media_url(file_name), 'message': '上传成功(DB 回退)'}
        except Exception as e:
            logger.error(f'数据库存储上传失败: {file_name}\n{e}')
            return {'url': None, 'message': str(e)}

    def delete(self, file_name: str) -> bool:
        try:
            from apps.media.models import MediaBlob
            MediaBlob.objects.filter(key=file_name).delete()
            return True
        except Exception as e:
            logger.error(f'数据库存储删除失败: {file_name}: {e}')
            return False

    def get_url(self, file_name: str) -> str:
        return db_media_url(file_name)


# ==================== R2 + 数据库回退（Django STORAGES 后端） ====================
# 商品媒体等以 default_storage（STORAGES）上传的路径，在 R2 断网时同样需要回退。
# 通过一个自定义后端：S3 失败 → 字节落库 → url() 返回 DB 读取端点。


def _media_in_db(name: str) -> bool:
    """判断某个 key 是否已走数据库回退存储。"""
    try:
        from apps.media.models import MediaBlob
        return MediaBlob.objects.filter(key=name).exists()
    except Exception:
        return False


def _media_to_db(name: str, content) -> str:
    """把文件内容写入 MediaBlob，返回落库 key。"""
    from apps.media.models import MediaBlob
    raw = content.read() if hasattr(content, 'read') else bytes(content)
    MediaBlob.objects.update_or_create(
        key=name,
        defaults={'content': raw, 'content_type': '', 'size': len(raw)},
    )
    return name


try:
    from storages.backends.s3boto3 import S3Boto3Storage
except Exception:  # pragma: no cover - django-storages 未安装
    S3Boto3Storage = None  # type: ignore


if S3Boto3Storage is None:  # pragma: no cover
    class R2DBFallbackStorage:  # type: ignore
        """占位：django-storages 未安装时不真正启用 R2。"""

        def __init__(self, *args, **kwargs):
            raise ImportError('请安装 django-storages[boto3] 以启用 R2 存储')
else:

    class R2DBFallbackStorage(S3Boto3Storage):
        """R2 + 读取侧双兜底（DB + 本地 pic/）。复用 S3Boto3Storage 读写配置。

        处理顺序严格保持「R2 → DB 回退 → 本地 pic/ 回退」：
          1. R2 可用  → 走 S3（原行为，不做任何探测）；
          2. R2 不可达 → 先查 DB 回退（MediaBlob，既有逻辑）；
          3. DB 也无   → 若启用本地回退（R2_FALLBACK_ENABLED）且本地 pic/
                        下存在同 key 文件，则回退到本地磁盘副本（读取侧兜底）。
        回退仅在确证 R2 不可达（含未配置/无外网/凭据缺失）且本地副本真实存在时
        发生，绝不静默伪造实体；最终 URL 恒以 pic/ 为前缀。

        R2 连通性探测结果做进程内短缓存（R2_AVAIL_PROBE_TTL），避免高并发下
        每个请求反复访问 R2 延迟判定。
        """

        # ── R2 连通性探测（进程级短缓存）──────────────────────────────
        _r2_avail_ts = 0.0          # 上次探测时刻（time.time）
        _r2_avail_value = True      # 上次探测结论；初始化默认可用（不阻断快路径）

        def _r2_available(self, force: bool = False) -> bool:
            """探测 R2 是否真正可写读；异常一律按「不可达」处理。

            判定方式：对 bucket 做一次无副作用探测（head_bucket），200 即视为
            可用；受网络/凭据/Endpoint 解析影响，任何异常都视为不可达。结果按
            R2_AVAIL_PROBE_TTL 缓存，force=True 强制刷新（健康检查用）。
            """
            ttl = float(getattr(settings, 'R2_AVAIL_PROBE_TTL', '30') or 30)
            now = _time.monotonic()
            if not force and now - self._r2_avail_ts < ttl:
                return self._r2_avail_value
            if not self.bucket_name:
                # 未配置 bucket（本地未注入 R2 凭据/未连外网）→ 直接判定不可达，免网络请求。
                ok = False
            else:
                try:
                    # S3Storage.connection 是 boto3 ServiceResource（含 .meta.client）。
                    # head_bucket 无副作用：200 = 可读写可达；任何错误（网络/凭据/404）→ 不可达。
                    self.connection.meta.client.head_bucket(Bucket=self.bucket_name)
                    ok = True
                except Exception as e:
                    logger.warning('R2 不可达（将尝试回退）: %s', e, exc_info=True)
                    ok = False
            self._r2_avail_ts = now
            self._r2_avail_value = ok
            return ok

        # ── 本地 pic/ 回退定位 ─────────────────────────────────────────
        @staticmethod
        def _local_fallback_root() -> str:
            """备用磁盘根：优先 settings.LOCAL_FALLBACK_ROOT，否则 MEDIA_ROOT/pic。"""
            root = getattr(settings, 'LOCAL_FALLBACK_ROOT', '') or ''
            if root:
                return root
            media_root = getattr(settings, 'MEDIA_ROOT', '') or ''
            return os.path.join(media_root, 'pic') if media_root else ''

        def _local_abs(self, name: str) -> str:
            """对象 key → 本地回退目录里的物理绝对路径（pic/<key>）。

            key 形如 products/2026/01/01/uuid.jpg（含日期分区子路径），
            直接在 pic/ 根下保持相同子结构，便于与 R2 key 一一对应。
            """
            safe = os.path.normpath(name)
            # 防路径逃逸：拒绝一切含 .. 的 key，避免落盘越出 pic 根。
            if not safe or safe == '..' or safe.startswith('../') or '/../' in safe or safe.endswith('/..'):
                raise ValueError(f'非法的对象 key: {name}')
            return os.path.join(self._local_fallback_root(), safe)

        def _local_exists(self, name: str) -> bool:
            """本地回退目录是否存在同名文件（读取侧兜底判定）。"""
            root = self._local_fallback_root()
            if not root:
                return False
            try:
                return os.path.isfile(self._local_abs(name))
            except ValueError:
                return False
            except Exception:
                return False

        # ── 核心读写（保持原顺序 + 最后本地回退）──────────────────────
        def _save(self, name, content):
            try:
                return super()._save(name, content)
            except Exception as e:
                logger.warning('R2 保存失败，落数据库回退: %s | %s', name, e)
                return _media_to_db(name, content)

        def url(self, name):
            # 顺序 1：DB 回退（既有逻辑，优先于 R2）
            if _media_in_db(name):
                return db_media_url(name)
            # 顺序 2：R2 可用 → 直接返回 R2 URL（不探测，快路径）
            if getattr(settings, 'R2_FALLBACK_ENABLED', True) and self._r2_available():
                return super().url(name)
            # 顺序 3：R2 不可达 → 本地 pic/ 有副本才回退
            if self._local_exists(name):
                return f'/media/pic/{name.strip("/")}'
            # R2 不可达且本地无副本：返回本地 pic/ 形态 URL，保持「以 pic/ 为前缀」，
            # 且绝不在 bucket None 时调用 super().url()（会因空 bucket 抛 ValueError）。
            return f'/media/pic/{name.strip("/")}'

        def delete(self, name):
            try:
                super().delete(name)
            except Exception as e:
                logger.warning('R2 删除失败: %s | %s', name, e)
            try:
                from apps.media.models import MediaBlob
                MediaBlob.objects.filter(key=name).delete()
            except Exception:
                pass

        def exists(self, name):
            try:
                if _media_in_db(name):
                    return True
            except Exception:
                pass
            # R2 可达 → 直接以 S3 为准
            if getattr(settings, 'R2_FALLBACK_ENABLED', True) and self._r2_available():
                return super().exists(name)
            # R2 不可达 → 以本地 pic/ 副本兜底；本地也没有则判定不存在。
            # 此刻绝不能回调 super().exists()：bucket 未配置（本地未注入 R2 凭据）
            # 时会因 head_object(None) 抛 TypeError 而非返回 False，破坏读取链路。
            return self._local_exists(name)


# ==================== 本地存储 (兼容旧代码) ====================

class LocalStorage(BaseStorage):
    """本地文件存储 (开发/降级用)"""

    def __init__(self):
        super().__init__()
        from django.core.files.storage import default_storage
        self.default_storage = default_storage
        # 公网媒体基础域名：优先用 PUBLIC_MEDIA_URL（生产可指向 api 域名/公网地址），
        # 否则回退 DOMAIN —— 避免 DOMAIN 为回环地址时上传返回 127.0.0.1 导致公网 Mixed Content。
        self.base_url = (
            getattr(settings, 'PUBLIC_MEDIA_URL', '')
            or getattr(settings, 'DOMAIN', 'http://localhost:8000')
        ).rstrip('/')

    def upload(self, file_name: str, file_content: bytes, content_type: str = None) -> dict:
        try:
            self.check_file_size(len(file_content))
            from django.core.files.base import ContentFile
            cf = ContentFile(file_content, name=file_name)
            self.default_storage.save(file_name, cf)
            url = self.default_storage.url(file_name)
            return {'url': f'{self.base_url}{url}', 'message': '上传成功'}
        except Exception as e:
            logger.error(f'本地 上传失败: {file_name}\n{e}')
            return {'url': None, 'message': str(e)}

    def delete(self, file_name: str) -> bool:
        try:
            self.default_storage.delete(file_name)
            return True
        except Exception as e:
            logger.error(f'本地 删除失败: {file_name}: {e}')
            return False

    def get_url(self, file_name: str) -> str:
        url = self.default_storage.url(file_name)
        return f'{self.base_url}{url}'


# ==================== 工厂函数 ====================

__storage__ = None


def get_storage() -> BaseStorage:
    """根据 FILE_STORAGE 配置返回对应存储后端。

    - 'r2'   → R2；上传失败（断网）自动回退数据库（见 R2Storage.upload）
    - 'db'   → 数据库存储（离线专用，字节落库）
    - 其他/默认 → 本地磁盘（离线可用）
    """
    global __storage__
    if __storage__ is not None:
        return __storage__

    backend = getattr(settings, 'FILE_STORAGE', 'local')
    if backend == 'r2':
        __storage__ = R2Storage()
    elif backend == 'db':
        __storage__ = DBStorage()
    else:
        __storage__ = LocalStorage()

    logger.info(f'存储后端已初始化: {__storage__.__class__.__name__}')
    return __storage__