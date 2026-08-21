"""HTTP-эндпоинт приёма пользовательских событий."""
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.dependencies import (
    get_auth_client,
    get_event_rate_limiter,
    get_event_service,
)
from api.v1.schemas.events import EventAcceptedResponse
from auth.exceptions import (
    AuthServiceContractError,
    AuthServiceUnavailableError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from core.event_rate_limit import RateLimiterUnavailableError
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


def _extract_bearer_authorization() -> str | None:
    """Вернуть корректный Authorization header или None."""
    authorization = request.headers.get(
        "Authorization",
    )

    if authorization is None:
        return None

    scheme, separator, token = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        return None

    return authorization


@router.post("/events")
def create_event():
    """Принять и опубликовать пользовательское событие."""
    request_id = get_request_id()

    authorization = _extract_bearer_authorization()

    if authorization is None:
        return (
            jsonify(
                {
                    "detail": "access_token_required",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.UNAUTHORIZED,
            {
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        current_user = get_auth_client().get_current_user(
            authorization=authorization,
            request_id=request_id,
        )
    except InvalidAccessTokenError:
        return (
            jsonify(
                {
                    "detail": "invalid_access_token",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.UNAUTHORIZED,
            {
                "WWW-Authenticate": "Bearer",
            },
        )
    except AuthUserForbiddenError:
        return (
            jsonify(
                {
                    "detail": "user_forbidden",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.FORBIDDEN,
        )
    except (
        AuthServiceUnavailableError,
        AuthServiceContractError,
    ):
        return (
            jsonify(
                {
                    "detail": "auth_service_unavailable",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

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

    if (
        event.user_id is not None
        and event.user_id != current_user.id
    ):
        return (
            jsonify(
                {
                    "detail": "event_user_mismatch",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.FORBIDDEN,
        )

    try:
        rate_limit = get_event_rate_limiter().check(
            current_user.id,
        )
    except RateLimiterUnavailableError:
        return (
            jsonify(
                {
                    "detail": "rate_limiter_unavailable",
                    "request_id": request_id,
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )

    if not rate_limit.allowed:
        response = jsonify(
            {
                "detail": "event_rate_limit_exceeded",
                "request_id": request_id,
            }
        )
        response.headers["Retry-After"] = str(
            rate_limit.retry_after_seconds
        )

        return (
            response,
            HTTPStatus.TOO_MANY_REQUESTS,
        )

    try:
        get_event_service().ingest(
            event=event,
            trusted_user_id=current_user.id,
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
        HTTPStatus.ACCEPTED,
    )
