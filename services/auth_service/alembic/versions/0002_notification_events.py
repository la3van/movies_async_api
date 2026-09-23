"""Outbox регистрации и неизменяемые снимки аудитории рассылок."""

from alembic import op

revision = "auth_notifications_2"
down_revision = "6604474198ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет транзакционные события и хранение аудитории."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.notification_events (
            event_id UUID PRIMARY KEY,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            published_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS notification_events_pending
        ON public.notification_events(created_at)
        WHERE published_at IS NULL
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.capture_notification_event()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE identity UUID := gen_random_uuid();
        BEGIN
            INSERT INTO public.notification_events(event_id, payload)
            VALUES (
                identity,
                jsonb_build_object(
                    'schema_version', 1,
                    'event_id', identity,
                    'kind', 'user.registered',
                    'aggregate_id', NEW.id,
                    'occurred_at', now()
                )
            );
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute("DROP TRIGGER IF EXISTS notification_created ON public.users")
    op.execute(
        """
        CREATE TRIGGER notification_created
        AFTER INSERT ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.capture_notification_event()
        """
    )
    op.execute(
        """
        CREATE TABLE notification_audiences (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE notification_audience_members (
            audience_id UUID NOT NULL
                REFERENCES notification_audiences(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            PRIMARY KEY (audience_id, user_id)
        )
        """
    )


def downgrade() -> None:
    """Запрещает откат с потерей истории событий и аудитории."""
    raise RuntimeError("Forward-only migration: preserve event history")
