"""Восстановление и защита обязательных системных шаблонов."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Возвращает ранее отключённые шаблоны и запрещает их архивирование."""
    op.execute("""
        UPDATE templates SET archived=false
        WHERE name IN ('user.registered', 'film.created')
    """)
    op.execute("""
        ALTER TABLE templates ADD CONSTRAINT system_templates_active
        CHECK (NOT archived OR name NOT IN ('user.registered', 'film.created'))
    """)


def downgrade() -> None:
    """Снимает ограничение, сохраняя восстановленные шаблоны активными."""
    op.execute("ALTER TABLE templates DROP CONSTRAINT system_templates_active")
