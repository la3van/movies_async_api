"""Настройка отображения технических моделей авторизации."""
from django.contrib import admin
from django.contrib.auth.models import Group, User


def unregister_model(
    model: type,
) -> None:
    """Безопасно удаляет модель из стандартной админки."""
    try:
        admin.site.unregister(
            model,
        )
    except admin.sites.NotRegistered:
        pass


unregister_model(User)
unregister_model(Group)
