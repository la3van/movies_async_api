"""HTTP-эндпоинт приёма пользовательских событий."""
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.dependencies import get_event_service
from api.v1.schemas.events import EventAcceptedResponse
from core.request_id import get_request_id
from models.events import EVENT_REQUEST_ADAPTER
from services.exceptions import EventIngestionUnavailable

router = Blueprint(
    "events",
    __name__,
)


def _serialize_validation_errors(
    error: ValidationError,
) -> list[dict]:
    """Подготовить ошибки Pydantic для безопасного JSON-ответа."""
    return [
        {
            "loc": [
                str(part)
                for part in item["loc"]
            ],
            "msg": item["msg"],
            "type": item["type"],
        }
        for item in error.errors(
            include_url=False,
        )
    ]


@router.post("/events")
def create_event():
    """Принять и опубликовать пользовательское событие."""
    request_id = get_request_id()

    raw_event = request.get_json(
        silent=True,
    )

    if not isinstance(raw_event, dict):
        return (
            jsonify(
                {
                    "detail": "invalid_json",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        event = EVENT_REQUEST_ADAPTER.validate_python(
            raw_event,
        )
    except ValidationError as exc:
        return (
            jsonify(
                {
                    "detail": "validation_error",
                    "request_id": request_id,
                    "errors": _serialize_validation_errors(
                        exc,
                    ),
                }
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    try:
        get_event_service().ingest(
            event=event,
            request_id=request_id,
        )
    except EventIngestionUnavailable:
        return (
            jsonify(
                {
                    "detail": "event_ingestion_unavailable",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    response = EventAcceptedResponse(
        event_id=event.event_id,
    )

    return (
        jsonify(
            response.model_dump(
                mode="json",
            )
        ),
        HTTPStatus.ACCEPTED
    )
