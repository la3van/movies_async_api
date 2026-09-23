"""Приложение FastAPI и управление общими ресурсами API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from api.management import router as management_router
from api.notifications import router
from core.config import get_settings
from core.database import create_engine
from core.telemetry import OPERATIONS, configure, shutdown, span
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import generate_latest
from repositories.postgres.catalog import Catalog
from repositories.postgres.notifications import PostgresNotifications
from services.notifications import NotificationService
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Открывает общие клиенты API и освобождает их при остановке."""
    settings = get_settings()
    configure(settings)
    engine = create_engine(settings)
    app.state.catalog = Catalog(engine, settings)
    app.state.engine = engine
    app.state.service = NotificationService(PostgresNotifications(engine))
    try:
        async with httpx.AsyncClient(
            base_url=settings.auth_base_url, timeout=5, follow_redirects=False
        ) as auth:
            app.state.auth = auth
            yield
    finally:
        await engine.dispose()
        shutdown()


app = FastAPI(
    title="Notification Service",
    lifespan=lifespan,
    docs_url="/notifications/docs",
    redoc_url="/notifications/redoc",
    openapi_url="/notifications/openapi.json",
)
app.include_router(router)
app.include_router(management_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Подтверждает, что HTTP-процесс приложения работает."""
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Проверяет доступность основных таблиц PostgreSQL."""
    try:
        async with app.state.engine.connect() as conn:
            await conn.execute(text("SELECT id FROM notifications LIMIT 0"))
            await conn.execute(text("SELECT event_id FROM outbox LIMIT 0"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise HTTPException(503, "database_unavailable") from exc
    return {"status": "ready"}


@app.middleware("http")
async def telemetry(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Создаёт HTTP-span и учитывает код ответа в метриках."""
    with span("notification.http", dict(request.headers)):
        response = await call_next(request)
        OPERATIONS.labels("http", str(response.status_code)).inc()
        return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Возвращает метрики процесса в формате Prometheus."""
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
