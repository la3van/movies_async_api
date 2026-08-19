"""Исключения сервисного слоя обработки пользовательских событий."""


class EventIngestionError(Exception):
    """Базовая ошибка при обработке пользовательского события."""


class EventIngestionUnavailable(EventIngestionError):
    """Событие временно невозможно передать в систему сбора данных."""
