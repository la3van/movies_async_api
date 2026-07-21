"""Конфигурация приложения интеграции с auth-service."""
from django.apps import AppConfig


class AdminAuthConfig(AppConfig):
    """Настройки приложения внешней авторизации."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_auth"
    verbose_name = "Авторизация"
