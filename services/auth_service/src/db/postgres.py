"""Модуль зависимостей относительно PostgreSQL."""
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

from opentelemetry.instrumentation.sqlalchemy import (
    SQLAlchemyInstrumentor,
)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей."""
    pass


engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def init_postgres() -> None:
    """Инициализирует подключение к PostgreSQL."""
    global engine, async_session_factory

    settings = get_settings()

    engine = create_async_engine(
        settings.postgres_url,
        echo=settings.debug,
        pool_pre_ping=True,
        connect_args={
            'timeout': settings.postgres_connect_timeout,
            'server_settings': {
                'statement_timeout': str(
                    settings.postgres_statement_timeout_ms,
                ),
            },
        },
    )

    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
    )

    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_postgres() -> None:
    """Закрывает соединения с PostgreSQL."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()

    engine = None
    async_session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Возвращает инициализированную фабрику PostgreSQL-сессий."""
    if async_session_factory is None:
        raise RuntimeError(
            'PostgreSQL session factory is not initialized',
        )

    return async_session_factory
