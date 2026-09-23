-- Событие сохраняется вместе с фильмом; ROLLBACK отменяет обе записи.
CREATE TABLE IF NOT EXISTS public.notification_events (
    event_id UUID PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS notification_events_pending
    ON public.notification_events(created_at)
    WHERE published_at IS NULL;

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
            'kind', 'film.created',
            'aggregate_id', NEW.id,
            'occurred_at', now(),
            'title', NEW.title
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS notification_created ON content.film_work;

CREATE TRIGGER notification_created
AFTER INSERT ON content.film_work
FOR EACH ROW
EXECUTE FUNCTION public.capture_notification_event();
