"""媒体回退读取 —— 从 DB / R2 读出字节回传给前端。

断网或 R2 不可达时，上传的文件字节落库（MediaBlob），本读写端点把字节以原
Content-Type 回传，保证离线也能展示图片/视频（serve_db_media）。

CDN 公网不可达、但 R2 对象存储本身有数据时，前端经 /api/media/r2/<key> 由
后端直接读取 R2 字节回传（serve_r2_media）。这是真正的「R2 真实数据源」兜底：
不依赖公网 CDN、不要求磁盘副本，服务端持有 R2 密钥即可命中。
"""
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def serve_db_media(request, key: str):
    """读取数据库回退存储中的一个媒体文件。"""
    from .models import MediaBlob

    blob = (
        MediaBlob.objects.filter(key=key)
        .only('content', 'content_type')
        .first()
    )
    if blob is None:
        return HttpResponse('Not Found', status=404)

    ctype = blob.content_type or 'application/octet-stream'
    response = HttpResponse(blob.content, content_type=ctype)
    response['Cache-Control'] = 'public, max-age=86400'  # 缓存 1 天，减轻读库压力
    return response


@require_GET
def serve_r2_media(request, key: str):
    """从 R2 对象存储直接读取对象字节并回传，作为 CDN 公网不可达时的兜底源。"""
    from utils.storage import get_storage

    storage = get_storage()
    read = getattr(storage, 'read', None)
    if read is None:
        return HttpResponse('Not Found', status=404)

    data, ctype = read(key)  # type: ignore[attr-defined]
    if data is None:
        return HttpResponse('Not Found', status=404)

    response = HttpResponse(data, content_type=ctype)
    # 兜底读 R2 也做长缓存，减少对 R2 的重复请求压力与带宽成本
    response['Cache-Control'] = 'public, max-age=86400'
    response['X-Fallback-Source'] = 'r2'
    return response