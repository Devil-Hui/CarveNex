from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.media'
    label = 'media'
    verbose_name = '媒体（DB 回退存储）'