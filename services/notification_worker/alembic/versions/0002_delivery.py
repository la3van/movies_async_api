"""Попытки отправки, аренда заданий и outbox результатов доставки."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    """Применяет изменения схемы текущей ревизии."""
    op.execute(
        (
            "ALTER TABLE delivery_jobs DROP CONSTRAINT "
            "delivery_jobs_status_check"
        )
    )
    op.execute("""ALTER TABLE delivery_jobs
        ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT
now(),
        ADD COLUMN lease_until TIMESTAMPTZ,
        ADD COLUMN claim_token UUID,
        ADD COLUMN error_code TEXT,
        ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        ADD CONSTRAINT valid_status CHECK(status IN
('pending','processing','retry','sent','failed'))
""")
    op.execute(
        (
            "CREATE INDEX delivery_due ON "
            "delivery_jobs(next_attempt_at) WHERE status "
            "IN ('pending','retry','processing')"
        )
    )
    op.execute("""CREATE TABLE outbox (
        event_id UUID PRIMARY KEY, topic TEXT NOT NULL,
message_key TEXT NOT NULL,
        payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL
DEFAULT now(),
        published_at TIMESTAMPTZ
    )""")
    op.execute(
        (
            "CREATE INDEX outbox_pending ON "
            "outbox(created_at) WHERE published_at IS NULL"
        )
    )


def downgrade():
    """Запрещает откат, который уничтожил бы историю доставки."""
    raise RuntimeError(
        "Forward-only migration: delivery history must be retained"
    )
