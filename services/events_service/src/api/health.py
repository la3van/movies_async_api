"""Эндпоинты проверки состояния сервиса."""

from http import HTTPStatus

from api.dependencies import get_event_service
from flask import Blueprint, jsonify

router = Blueprint(
    "health",
    __name__,
)


@router.get("/health")
def health():
    """Проверить работоспособность процесса приложения."""
    return (
        jsonify(
            {
                "status": "ok",
            }
        ),
        HTTPStatus.OK,
    )


@router.get("/ready")
def ready():
    """Проверить готовность сервиса принимать события."""
    if not get_event_service().is_ready():
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "dependency": "kafka",
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    return (
        jsonify(
            {
                "status": "ready",
            }
        ),
        HTTPStatus.OK,
    )
