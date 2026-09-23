"""Создание ограниченного пула соединений PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Создаёт пул PostgreSQL с ограничениями и таймаутами."""
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"timeout": 5, "command_timeout": 30},
    )
