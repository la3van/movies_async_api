"""Profile application and resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from api.v1.endpoints.profiles import internal_router, router
from auth.client import AuthClient
from core.config import Settings, get_settings
from core.middleware import PrivacyMiddleware
from core.security import ProfileCipher
from core.telemetry import initialize
from db.postgres import create_engine
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from services.exceptions import ProfileError
from services.profile import ProfileService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from unit_of_work.postgres import SQLAlchemyUnitOfWork


def create_app(
    settings: Settings | None = None,
    *,
    auth_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings or get_settings()
        engine = create_engine(config)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        provider = initialize()
        cipher = ProfileCipher(
            config.encryption_keys.get_secret_value(),
            config.phone_index_key.get_secret_value(),
        )
        try:
            async with httpx.AsyncClient(
                transport=auth_transport,
                base_url=config.auth_base_url,
                timeout=config.http_timeout_seconds,
            ) as client:
                app.state.settings = config
                app.state.engine = engine
                app.state.session_factory = factory
                app.state.profile_service = ProfileService(
                    lambda: SQLAlchemyUnitOfWork(factory), cipher
                )
                app.state.auth_client = AuthClient(client)
                yield
        finally:
            await engine.dispose()
            if provider is not None:
                provider.shutdown()

    app = FastAPI(
        title="Profile Service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/profiles/docs",
        openapi_url="/profiles/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(PrivacyMiddleware)
    app.include_router(router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/api/v1")

    @app.middleware("http")
    async def tracing(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        with trace.get_tracer("profiles").start_as_current_span(
            "profiles.http",
            record_exception=False,
            set_status_on_exception=False,
        ):
            return await call_next(request)

    @app.exception_handler(ProfileError)
    async def domain_error(
        request: Request, exc: ProfileError
    ) -> JSONResponse:
        return JSONResponse({"detail": exc.code}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            {
                "detail": [
                    {
                        "loc": error["loc"],
                        "type": error["type"],
                        "msg": "Invalid value",
                    }
                    for error in exc.errors()
                ]
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": "internal_error"},
            500,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/health", include_in_schema=False)
    @app.get("/profiles/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", include_in_schema=False)
    @app.get("/profiles/ready", include_in_schema=False)
    async def ready(request: Request) -> JSONResponse:
        try:
            async with request.app.state.engine.connect() as connection:
                await connection.execute(
                    text("SELECT user_id FROM profiles LIMIT 1")
                )
        except Exception:
            return JSONResponse({"status": "unavailable"}, 503)
        return JSONResponse({"status": "ready"})

    return app


app = create_app()
