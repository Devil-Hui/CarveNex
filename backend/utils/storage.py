"""文件存储工具类 —— 工厂模式 (Local / Cloudflare R2)

Usage:
    from utils.storage import get_storage

    storage = get_storage()
    result = storage.upload(file_name, file_content, content_type='image/jpeg')
    url = storage.get_url(file_name)
    storage.delete(file_name)
"""

import logging
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
        """S3/R2 上传失败（断网）时自动落库；url()/delete()/exists() 感知 DB 回退。

        作为 STORAGES['default'] 的后端，复用 S3Boto3Storage 的读配（settings 里的
        AWS_* 与 R2 相关类属性），仅对存储/寻址做「S3 → DB」回退降级。
        """

        def _save(self, name, content):
            try:
                return super()._save(name, content)
            except Exception as e:
                logger.warning('S3/R2 保存失败，落数据库回退: %s | %s', name, e)
                return _media_to_db(name, content)

        def url(self, name):
            if _media_in_db(name):
                return db_media_url(name)
            return super().url(name)

        def delete(self, name):
            try:
                super().delete(name)
            except Exception as e:
                logger.warning('S3/R2 删除失败: %s | %s', name, e)
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
            return super().exists(name)


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