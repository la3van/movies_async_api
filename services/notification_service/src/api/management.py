"""HTTP-методы управления шаблонами, рассылками и статусами."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from models.management import CampaignInput, TemplateCreate, TemplateInput
from repositories.interfaces.notifications import IdempotencyConflict
from repositories.postgres.catalog import MissingResource
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.auth import require_superuser

router = APIRouter(
    prefix="/api/v1/notifications", dependencies=[Depends(require_superuser)]
)


@router.post("/templates", status_code=201)
async def create_template(body: TemplateCreate, request: Request) -> Any:
    """Создаёт шаблон или возвращает конфликт занятого имени."""
    try:
        return await request.app.state.catalog.template(body)
    except IntegrityError as exc:
        raise HTTPException(409, "template_name_exists") from exc


@router.put("/templates/{template_id}")
async def version_template(
    template_id: UUID, body: TemplateInput, request: Request
) -> Any:
    """Добавляет неизменяемую версию существующего шаблона."""
    try:
        return await request.app.state.catalog.template(body, template_id)
    except MissingResource as exc:
        raise HTTPException(404, "template_not_found") from exc


@router.get("/templates")
async def templates(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Any:
    """Возвращает страницу шаблонов, включая архивные."""
    async with request.app.state.engine.connect() as conn:
        rows = await conn.execute(
            text(
                (
                    "SELECT id,name,archived FROM templates ORDER "
                    "BY name LIMIT :limit OFFSET :offset"
                )
            ),
            dict(limit=limit, offset=offset),
        )
        return [dict(row) for row in rows.mappings()]


@router.get("/templates/{template_id}")
async def template(
    template_id: UUID,
    request: Request,
    version: int | None = Query(None, ge=1),
) -> Any:
    """Возвращает выбранный или последний доступный снимок шаблона."""
    try:
        async with request.app.state.engine.connect() as conn:
            return await request.app.state.catalog.snapshot(
                conn, template_id, version
            )
    except MissingResource as exc:
        raise HTTPException(404, "template_not_found") from exc


@router.delete("/templates/{template_id}", status_code=204)
async def archive(template_id: UUID, request: Request) -> None:
    """Архивирует шаблон, сохраняя ранее созданные версии."""
    async with request.app.state.engine.begin() as conn:
        result = await conn.execute(
            text(
                "UPDATE templates SET archived=true WHERE id=:id RETURNING id"
            ),
            dict(id=template_id),
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(404, "template_not_found")


@router.post("/campaigns", status_code=202)
async def campaign(
    body: CampaignInput,
    request: Request,
    actor: Annotated[UUID, Depends(require_superuser)],
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[!-~]+$")
    ],
) -> dict[str, UUID]:
    """Создаёт идемпотентную рассылку по снимку версии шаблона."""
    try:
        identity = await request.app.state.catalog.campaign(
            actor, idempotency_key, body
        )
        return {"campaign_id": identity}
    except MissingResource as exc:
        raise HTTPException(404, "template_not_found") from exc
    except IdempotencyConflict as exc:
        raise HTTPException(409, "idempotency_key_conflict") from exc


@router.get("/campaigns/{campaign_id}")
async def campaign_status(campaign_id: UUID, request: Request) -> Any:
    """Возвращает прогресс подготовки и счётчики статусов доставки."""
    async with request.app.state.engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text(
                        (
                            "SELECT id,state,expanded_count,scheduled_at "
                            "FROM campaigns WHERE id=:id"
                        )
                    ),
                    dict(id=campaign_id),
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise HTTPException(404, "campaign_not_found")
        counts = (
            (
                await conn.execute(
                    text(
                        (
                            "SELECT status,count(*) AS count FROM "
                            "notifications WHERE campaign_id=:id GROUP BY "
                            "status"
                        )
                    ),
                    dict(id=campaign_id),
                )
            )
            .mappings()
            .all()
        )
        return {
            **dict(row),
            "deliveries": {r["status"]: r["count"] for r in counts},
        }


@router.get("/{notification_id}")
async def notification_status(notification_id: UUID, request: Request) -> Any:
    """Возвращает сохранённый статус и номер попытки уведомления."""
    async with request.app.state.engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text(
                        (
                            "SELECT "
                            "id,delivery_id,status,attempt,error_code, "
                            "updated_at "
                            "FROM notifications WHERE id=:id"
                        )
                    ),
                    dict(id=notification_id),
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise HTTPException(404, "notification_not_found")
        return dict(row)
