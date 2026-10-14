"""One database and transaction boundary owned by Profile Service."""

from core.config import Settings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.postgres_url,
        pool_pre_ping=True,
        echo=False,
        hide_parameters=True,
    )
