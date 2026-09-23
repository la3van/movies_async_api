"""Сохраняемая пауза отправки при ошибке SMTP-авторизации."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт общую для отправителей блокировку и аренду проверки SMTP."""
    op.execute("""
        CREATE TABLE smtp_state (
            id INTEGER PRIMARY KEY CHECK (id=1),
            blocked BOOLEAN NOT NULL DEFAULT false,
            probe_after TIMESTAMPTZ NOT NULL DEFAULT now(),
            probe_token UUID
        )
    """)
    op.execute("INSERT INTO smtp_state (id) VALUES (1)")


def downgrade() -> None:
    """Удаляет служебную блокировку без изменения заданий доставки."""
    op.execute("DROP TABLE smtp_state")
