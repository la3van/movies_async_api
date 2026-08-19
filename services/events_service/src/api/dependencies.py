"""Получение зависимостей HTTP API."""
from typing import cast

from flask import current_app

from services.events import EventService


def get_event_service() -> EventService:
    """Получить сервис обработки пользовательских событий."""
    return cast(
        EventService,
        current_app.extensions["event_service"],
    )
