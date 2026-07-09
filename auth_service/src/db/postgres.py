"""Модуль зависимостей относительно PostgreSQL."""
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import DeclarativeBase

from core.config import get_settings


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


async def get_session() -> AsyncIterator[AsyncSession]:
    """Возвращает PostgreSQL-сессию для dependency injection."""
    if async_session_factory is None:
        raise RuntimeError('PostgreSQL session factory is not initialized')

    async with async_session_factory() as session:
        yield session
