"""Отправка писем из PostgreSQL с сохраняемыми повторами."""

import asyncio
import logging

import httpx
from core.config import get_settings
from core.database import create_engine
from core.health import beat, unready
from core.runtime import pause, supervise
from core.telemetry import OPERATIONS, span
from models.contract import DeliveryJob
from repositories.postgres.delivery import DeliveryRepository
from services.delivery import DeliveryService, PermanentFailure


async def run(stop: asyncio.Event) -> None:
    """Захватывает задания, отправляет письма и сохраняет исход попыток."""
    settings = get_settings()
    if not settings.internal_token.get_secret_value():
        raise RuntimeError("INTERNAL_TOKEN must be configured")
    engine = create_engine(settings)
    repository = DeliveryRepository(engine, settings)
    try:
        async with httpx.AsyncClient(
            base_url=settings.auth_base_url, timeout=5
        ) as client:
            delivery = DeliveryService(settings, client)
            while not stop.is_set():
                try:
                    row = await repository.claim()
                    if row is None:
                        beat()
                        await pause(stop, settings.poll_seconds)
                        continue
                    state, error, delay = "sent", None, 0.0
                    try:
                        if row["attempt"] > settings.max_attempts:
                            raise PermanentFailure("attempts_exhausted")
                        job = DeliveryJob.model_validate(row["payload"])
                        with span(
                            "email.send",
                            {
                                "traceparent": job.trace_context.traceparent
                                or ""
                            },
                        ):
                            await delivery.send(job)
                    except PermanentFailure as exc:
                        state, error = "failed", str(exc)
                    except Exception:
                        error = "transient_delivery_failure"
                        state = (
                            "failed"
                            if row["attempt"] >= settings.max_attempts
                            else "retry"
                        )
                        delay = delivery.delay(row["attempt"])
                    await repository.finish(row, state, error, delay)
                    OPERATIONS.labels("delivery", state).inc()
                    beat()
                except Exception:
                    unready()
                    logging.getLogger(__name__).error(
                        "Delivery iteration failed"
                    )
                    await pause(stop, settings.poll_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
