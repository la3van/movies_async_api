"""Начальная схема хранения уведомлений и заданий доставки."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Применяет изменения схемы текущей ревизии."""
    op.execute("""CREATE TABLE delivery_jobs (
        delivery_id UUID PRIMARY KEY,
        event_id UUID NOT NULL,
        notification_id UUID NOT NULL,
        payload JSONB NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status =
'pending'),
        received_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")


def downgrade():
    """Откатывает начальную схему базы данных."""
    op.drop_table("delivery_jobs")
