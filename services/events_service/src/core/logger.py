"""Настройка логирования сервиса."""

import logging

from core.request_id import (
    get_request_id,
)
from flask import (
    has_request_context,
)


class RequestIdFilter(logging.Filter):
    """Добавить идентификатор HTTP-запроса в записи логов."""

    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        """Дополнить запись лога идентификатором текущего запроса."""
        if has_request_context():
            record.request_id = get_request_id() or "-"
        else:
            record.request_id = "-"

        return True


LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "[request_id=%(request_id)s] %(message)s "
)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": RequestIdFilter,
        },
    },
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": [
                "request_id",
            ],
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
        ],
    },
}
