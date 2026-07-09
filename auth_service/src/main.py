"""Точка входа FastAPI-приложения auth-сервиса."""
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

app = FastAPI(
    title="auth-service",
    decription="Сервис авторизации и аутентификации для онлайн-кинотеатра",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Проверяет, что auth-сервис запущен."""

    return {"status": "ok"}
