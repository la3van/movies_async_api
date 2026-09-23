"""Шаблоны, рассылки и состояние доставки в базе Notification API."""

import json

from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    """Применяет изменения схемы текущей ревизии."""
    op.execute(
        (
            "ALTER TABLE notifications ADD COLUMN status "
            "TEXT NOT NULL DEFAULT 'pending', ADD COLUMN "
            "attempt INTEGER NOT NULL DEFAULT 0, ADD "
            "COLUMN error_code TEXT, ADD COLUMN updated_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now(), ADD "
            "COLUMN campaign_id UUID"
        )
    )
    op.execute(
        (
            "ALTER TABLE outbox ADD COLUMN topic TEXT NOT "
            "NULL DEFAULT 'notification-delivery-v1', ADD "
            "COLUMN message_key TEXT"
        )
    )
    op.execute("UPDATE outbox SET message_key=payload->>'delivery_id'")
    op.execute("ALTER TABLE outbox ALTER COLUMN message_key SET NOT NULL")
    op.execute("ALTER TABLE outbox DROP CONSTRAINT outbox_notification_id_key")
    op.execute("ALTER TABLE outbox ALTER COLUMN notification_id DROP NOT NULL")
    op.execute(
        (
            "CREATE TABLE inbox (event_id UUID PRIMARY "
            "KEY, received_at TIMESTAMPTZ NOT NULL DEFAULT "
            "now())"
        )
    )
    op.execute(
        (
            "CREATE TABLE templates (id UUID PRIMARY KEY, "
            "name TEXT NOT NULL UNIQUE, archived BOOLEAN "
            "NOT NULL DEFAULT false)"
        )
    )
    op.execute(
        (
            "CREATE TABLE template_versions (template_id "
            "UUID NOT NULL REFERENCES templates(id), "
            "version INTEGER NOT NULL, snapshot JSONB NOT "
            "NULL, PRIMARY KEY(template_id,version))"
        )
    )
    op.execute("""CREATE TABLE campaigns (
        id UUID PRIMARY KEY, actor_id UUID NOT NULL,
idempotency_key TEXT NOT NULL,
        request JSONB NOT NULL, snapshot JSONB NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending', cursor UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expanded_count INTEGER NOT NULL DEFAULT 0,
        UNIQUE(actor_id,idempotency_key)
    )""")
    op.execute(
        (
            "CREATE INDEX campaigns_pending ON "
            "campaigns(scheduled_at) WHERE state != "
            "'expanded'"
        )
    )
    op.execute(
        ("CREATE INDEX notifications_campaign ON notifications(campaign_id)")
    )
    for key, name, subject, body in [
        (
            "11111111-1111-4111-8111-111111111111",
            "user.registered",
            "Добро пожаловать!",
            "Здравствуйте, {{ first_name }}! Рады видеть вас в кинотеатре.",
        ),
        (
            "22222222-2222-4222-8222-222222222222",
            "film.created",
            "Новый фильм",
            (
                "Здравствуйте, {{ first_name }}! В каталоге появился фильм {{ "
                "film_title }}."
            ),
        ),
    ]:
        op.get_bind().execute(
            text("INSERT INTO templates(id,name) VALUES (:id,:name)"),
            dict(id=key, name=name),
        )
        op.get_bind().execute(
            text(
                "INSERT INTO template_versions VALUES (:id,1,CAST(:s AS "
                "JSONB))"
            ),
            dict(
                id=key,
                s=json.dumps(
                    dict(
                        template_id=key,
                        version=1,
                        subject=subject,
                        body=body,
                        body_format="text",
                    )
                ),
            ),
        )


def downgrade():
    """Запрещает откат, который уничтожил бы историю доставки."""
    raise RuntimeError(
        "Forward-only migration: delivery history must be retained"
    )
