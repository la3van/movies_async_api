"""Конфигурация приложения интеграции с auth-service."""

from importlib import import_module

from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class ProfileAdminConfig(AdminConfig):
    default_site = "admin_auth.site.ProfileAdminSite"


class AdminAuthConfig(AppConfig):
    """Настройки приложения внешней авторизации."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_auth"
    verbose_name = "Авторизация"

    def ready(self) -> None:
        import_module("admin_auth.signals")
