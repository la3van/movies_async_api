"""Окружение Alembic для асинхронного подключения к PostgreSQL."""

import asyncio

from alembic import context
from core.config import get_settings
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config


def migrate(connection):
    """Применяет миграции в транзакции переданного соединения."""
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    """Запускает миграции через асинхронное соединение PostgreSQL."""
    engine = create_async_engine(
        get_settings().database_url, poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=get_settings().database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
