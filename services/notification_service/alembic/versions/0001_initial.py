"""Начальная схема хранения уведомлений и заданий доставки."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Применяет изменения схемы текущей ревизии."""
    op.execute("""CREATE TABLE notifications (
        id UUID PRIMARY KEY,
        delivery_id UUID NOT NULL UNIQUE,
        actor_id UUID NOT NULL,
        idempotency_key VARCHAR(128) NOT NULL,
        request JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(actor_id, idempotency_key)
    )""")
    op.execute("""CREATE TABLE outbox (
        event_id UUID PRIMARY KEY,
        notification_id UUID NOT NULL UNIQUE REFERENCES
notifications(id),
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        published_at TIMESTAMPTZ
    )""")
    op.execute(
        "CREATE INDEX outbox_pending ON outbox(created_at) "
        "WHERE published_at IS NULL"
    )


def downgrade():
    """Откатывает начальную схему базы данных."""
    op.drop_table("outbox")
    op.drop_table("notifications")
