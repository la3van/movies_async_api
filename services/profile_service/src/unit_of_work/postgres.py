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
        """Закрывает сессию, сохраняя исходную ошибку операции."""
        cleanup_error: BaseException | None = None

        try:
            await self.session.rollback()
        except BaseException as error:
            cleanup_error = error
        finally:
            try:
                await self.session.close()
            except BaseException as error:
                if cleanup_error is None:
                    cleanup_error = error

        if exc is None and cleanup_error is not None:
            raise cleanup_error

    async def commit(self) -> None:
        await self.session.commit()
