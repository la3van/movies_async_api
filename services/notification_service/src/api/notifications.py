"""HTTP-метод идемпотентного создания уведомления."""

from typing import Annotated, cast
from uuid import UUID, uuid4

from core.telemetry import carrier
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from models.contract import Accepted, CreateNotification, TraceContext
from repositories.interfaces.notifications import IdempotencyConflict
from services.notifications import NotificationService

from api.auth import require_superuser

router = APIRouter()


@router.post("/api/v1/notifications", status_code=202, response_model=Accepted)
async def create_notification(
    body: CreateNotification,
    request: Request,
    actor: Annotated[UUID, Depends(require_superuser)],
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    ],
    x_request_id: Annotated[
        str | None, Header(min_length=1, max_length=128)
    ] = None,
    traceparent: Annotated[
        str | None,
        Header(pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"),
    ] = None,
) -> Accepted:
    """Принимает заявку и возвращает её устойчивые идентификаторы."""
    trace = TraceContext(
        request_id=x_request_id or str(uuid4()),
        traceparent=carrier().get("traceparent") or traceparent,
    )
    try:
        service = cast(NotificationService, request.app.state.service)
        return await service.create(
            actor,
            idempotency_key,
            body,
            trace,
        )
    except IdempotencyConflict as exc:
        raise HTTPException(409, "idempotency_key_conflict") from exc
