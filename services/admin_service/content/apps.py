"""Конфигурация приложения управления контентом."""
from django.apps import AppConfig


class ContentConfig(AppConfig):
    """Настройки приложения контента."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = "Контент"
