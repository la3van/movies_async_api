"""A fresh session per use case, with rollback on any failure."""

from types import TracebackType

from repositories.interfaces.profile import ProfileRepository
from repositories.postgres.profile import PostgresProfileRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyUnitOfWork:
    profiles: ProfileRepository

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._factory()
        self.profiles = PostgresProfileRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()
