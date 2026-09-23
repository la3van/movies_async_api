"""Хранение версий шаблонов и прогресса массовых рассылок."""

import json
from typing import Any
from uuid import UUID, uuid4, uuid5

from core.config import Settings
from models.contract import DeliveryJob, TemplateSnapshot, TraceContext
from models.management import CampaignInput, TemplateCreate, TemplateInput
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from repositories.interfaces.notifications import IdempotencyConflict


class MissingResource(Exception):
    """Шаблон или его запрошенная версия недоступны."""

    pass


async def enqueue(
    conn: AsyncConnection,
    job: DeliveryJob,
    actor: UUID,
    key: str,
    topic: str,
    campaign: UUID | None = None,
) -> None:
    """Сохраняет уведомление и outbox в транзакции вызывающего кода."""
    request = job.model_dump(
        mode="json", include={"user_id", "channel", "template", "context"}
    )
    result = await conn.execute(
        text("""
        INSERT INTO
notifications(id,delivery_id,actor_id,idempotency_key,request,campaign_id)
        VALUES (:id,:delivery,:actor,:key,CAST(:request AS
JSONB),:campaign)
        ON CONFLICT(actor_id,idempotency_key) DO NOTHING
RETURNING id
"""),
        dict(
            id=job.notification_id,
            delivery=job.delivery_id,
            actor=actor,
            key=key,
            request=json.dumps(request),
            campaign=campaign,
        ),
    )
    if result.scalar_one_or_none() is not None:
        await conn.execute(
            text("""
            INSERT INTO
outbox(event_id,notification_id,payload,topic,message_key)
            VALUES (:event,:id,CAST(:payload AS
JSONB),:topic,:key)
"""),
            dict(
                event=job.event_id,
                id=job.notification_id,
                payload=job.model_dump_json(),
                topic=topic,
                key=str(job.delivery_id),
            ),
        )


class Catalog:
    """Репозиторий шаблонов и состояния массовых рассылок."""

    def __init__(self, engine: AsyncEngine, settings: Settings) -> None:
        """Сохраняет подключение PostgreSQL и параметры очередей."""
        self.engine, self.settings = engine, settings

    async def snapshot(
        self,
        conn: AsyncConnection,
        template_id: UUID,
        version: int | None = None,
    ) -> TemplateSnapshot:
        """Загружает выбранную или последнюю версию активного шаблона."""
        value = (
            await conn.execute(
                text("""
            SELECT v.snapshot FROM template_versions v JOIN
templates t ON t.id=v.template_id
            WHERE t.id=:id AND NOT t.archived
              AND (CAST(:version AS INTEGER) IS NULL OR
v.version=:version)
            ORDER BY v.version DESC LIMIT 1
"""),
                dict(id=template_id, version=version),
            )
        ).scalar_one_or_none()
        if value is None:
            raise MissingResource
        return TemplateSnapshot.model_validate(value)

    async def template(
        self, body: TemplateInput, template_id: UUID | None = None
    ) -> TemplateSnapshot:
        """Создаёт шаблон или новую версию под блокировкой его строки."""
        async with self.engine.begin() as conn:
            if template_id is None:
                if not isinstance(body, TemplateCreate):
                    raise ValueError("Name required")
                template_id = uuid4()
                await conn.execute(
                    text("INSERT INTO templates(id,name) VALUES (:id,:name)"),
                    dict(id=template_id, name=body.name),
                )
                version = 1
            else:
                row = (
                    await conn.execute(
                        text(
                            (
                                "SELECT id FROM templates WHERE id=:id "
                                "AND NOT "
                                "archived FOR UPDATE"
                            )
                        ),
                        dict(id=template_id),
                    )
                ).first()
                if row is None:
                    raise MissingResource
                version = (
                    int(
                        (
                            await conn.execute(
                                text(
                                    (
                                        "SELECT max(version) FROM "
                                        "template_versions "
                                        "WHERE template_id=:id"
                                    )
                                ),
                                dict(id=template_id),
                            )
                        ).scalar_one()
                    )
                    + 1
                )
            snapshot = TemplateSnapshot(
                template_id=template_id,
                version=version,
                subject=body.subject,
                body=body.body,
                body_format=body.body_format,
            )
            await conn.execute(
                text(
                    (
                        "INSERT INTO template_versions VALUES "
                        "(:id,:version,CAST(:snapshot AS JSONB))"
                    )
                ),
                dict(
                    id=template_id,
                    version=version,
                    snapshot=snapshot.model_dump_json(),
                ),
            )
            return snapshot

    async def campaign(
        self, actor: UUID, key: str, body: CampaignInput
    ) -> UUID:
        """Создаёт идемпотентную рассылку по снимку версии шаблона."""
        request = body.model_dump(mode="json")
        async with self.engine.begin() as conn:
            await conn.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                dict(key=f"{actor}:{key}"),
            )
            old = (
                (
                    await conn.execute(
                        text(
                            (
                                "SELECT id,request FROM campaigns "
                                "WHERE "
                                "actor_id=:actor AND idempotency_key=:key"
                            )
                        ),
                        dict(actor=actor, key=key),
                    )
                )
                .mappings()
                .first()
            )
            if old:
                if old["request"] != request:
                    raise IdempotencyConflict
                return UUID(str(old["id"]))
            snapshot = await self.snapshot(
                conn, body.template_id, body.version
            )
            identity = uuid4()
            await conn.execute(
                text("""
                INSERT INTO
campaigns(id,actor_id,idempotency_key,request,snapshot,scheduled_at)
                VALUES (:id,:actor,:key,CAST(:request AS
JSONB),CAST(:snapshot AS JSONB),COALESCE(:scheduled,now()))
"""),
                dict(
                    id=identity,
                    actor=actor,
                    key=key,
                    request=json.dumps(request),
                    snapshot=snapshot.model_dump_json(),
                    scheduled=body.scheduled_at,
                ),
            )
            return identity

    async def expand_page(
        self, conn: AsyncConnection, row: Any, users: list[UUID]
    ) -> None:
        """Сохраняет задания страницы и курсор в одной транзакции."""
        for user in users:
            identity = uuid5(row["id"], str(user))
            job = DeliveryJob(
                user_id=user,
                template=TemplateSnapshot.model_validate(row["snapshot"]),
                context=row["request"].get("context", {}),
                notification_id=identity,
                delivery_id=uuid5(identity, "email"),
                event_id=uuid5(identity, "delivery-v1"),
                trace_context=TraceContext(request_id=str(row["id"])),
            )
            await enqueue(
                conn,
                job,
                row["actor_id"],
                str(identity),
                self.settings.jobs_topic,
                row["id"],
            )
        await conn.execute(
            text("""
            UPDATE campaigns SET cursor=:cursor,
expanded_count=expanded_count+:size,
                state=:state WHERE id=:id
"""),
            dict(
                cursor=users[-1] if users else row["cursor"],
                size=len(users),
                state="expanding" if users else "expanded",
                id=row["id"],
            ),
        )
