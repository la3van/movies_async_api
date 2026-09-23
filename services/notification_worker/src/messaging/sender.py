"""Отправка писем из PostgreSQL с сохраняемыми повторами."""

import asyncio
import logging

import httpx
from core.config import get_settings
from core.database import create_engine
from core.health import beat, unready
from core.runtime import pause, supervise
from core.telemetry import DELIVERY_ERRORS, OPERATIONS, span
from models.contract import DeliveryJob
from repositories.postgres.delivery import DeliveryRepository
from services.delivery import (
    DeliveryService,
    PermanentFailure,
    SMTPConfigurationFailure,
    TransientFailure,
)

log = logging.getLogger(__name__)
SAFE_ERRORS = {
    "auth_unavailable",
    "invalid_auth_response",
    "smtp_temporary_failure",
    "smtp_authentication_failed",
    "smtp_probe_failed",
    "transient_delivery_failure",
    "recipient_unavailable",
    "recipient_rejected",
    "smtp_rejected",
    "invalid_template",
    "invalid_smtp_config",
    "attempts_exhausted",
}


def report_failure(code: str) -> str:
    """Публикует только разрешённый код, без исключения и данных письма."""
    safe = code if code in SAFE_ERRORS else "transient_delivery_failure"
    DELIVERY_ERRORS.labels(safe).inc()
    log.error("Delivery failure: %s", safe)
    return safe


async def run(stop: asyncio.Event) -> None:
    """Отправляет задания, учитывая общую паузу и причины ошибок."""
    settings = get_settings()
    if not settings.internal_token.get_secret_value():
        raise RuntimeError("INTERNAL_TOKEN must be configured")
    engine = create_engine(settings)
    repository = DeliveryRepository(engine, settings)
    degraded = False
    try:
        async with httpx.AsyncClient(
            base_url=settings.auth_base_url, timeout=5
        ) as client:
            delivery = DeliveryService(settings, client)
            while not stop.is_set():
                try:
                    if await repository.smtp_blocked():
                        unready()
                        token = await repository.claim_smtp_probe()
                        if token is not None:
                            try:
                                await delivery.check_smtp()
                            except Exception:
                                report_failure("smtp_probe_failed")
                                await repository.finish_smtp_probe(
                                    token, False
                                )
                            else:
                                await repository.finish_smtp_probe(token, True)
                                log.info("SMTP connection restored")
                        await pause(stop, settings.poll_seconds)
                        continue
                    row = await repository.claim()
                    if row is None:
                        if not degraded:
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
                    except SMTPConfigurationFailure:
                        unready()
                        report_failure("smtp_authentication_failed")
                        await repository.pause_smtp(row)
                        continue
                    except PermanentFailure as exc:
                        state, error = "failed", report_failure(str(exc))
                    except TransientFailure as exc:
                        error = report_failure(str(exc))
                    except httpx.RequestError:
                        error = report_failure("auth_unavailable")
                    except Exception:
                        error = report_failure("transient_delivery_failure")
                    if error is not None and state != "failed":
                        degraded = True
                        unready()
                        state = (
                            "failed"
                            if row["attempt"] >= settings.max_attempts
                            else "retry"
                        )
                        delay = delivery.delay(row["attempt"])
                    saved = await repository.finish(row, state, error, delay)
                    if saved:
                        OPERATIONS.labels("delivery", state).inc()
                    if saved and state == "sent":
                        degraded = False
                        beat()
                    elif not degraded:
                        beat()
                except Exception:
                    degraded = True
                    unready()
                    log.error("Delivery iteration failed")
                    await pause(stop, settings.poll_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
