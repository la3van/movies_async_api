"""Настройка отображения технических моделей авторизации."""

from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.auth.models import Group, User
from django.db.models import Model


def unregister_model(
    model: type[Model],
) -> None:
    """Безопасно удаляет модель из стандартной админки."""
    try:
        admin.site.unregister(
            model,
        )
    except NotRegistered:
        pass


unregister_model(User)
unregister_model(Group)
