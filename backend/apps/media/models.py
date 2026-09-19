"""媒体字节回退存储 —— 断网/R2 不可达时把文件字节落库，读取时再回传给前端。

需求背景：离线或远程对象存储（Cloudflare R2）不可达时，仍能把图片/视频等
媒体内容「存到数据库、读到数据库」，保证无外网也能正常上传与展示。
"""
from django.db import models


class MediaBlob(models.Model):
    """一个媒体文件的内容落库（key 即对象存储 key，含日期分区 + UUID）。"""

    key = models.CharField('对象 key', max_length=255, unique=True, db_index=True)
    content_type = models.CharField('内容类型', max_length=120, default='', blank=True)
    size = models.BigIntegerField('字节数', default=0)
    # 内容字节（MySQL longblob，覆盖常见图片/视频回退；单文件超限会被存储层拒绝）
    content = models.BinaryField('内容字节')

    class Meta:
        app_label = 'media'
        db_table = 'media_blob'
        verbose_name = '媒体回退存储'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'MediaBlob({self.key}, {self.size} bytes)'