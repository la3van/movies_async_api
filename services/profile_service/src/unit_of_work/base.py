"""Transaction protocol, matching the Auth Service layering."""

from collections.abc import Callable
from types import TracebackType
from typing import Protocol

from repositories.interfaces.profile import ProfileRepository


class UnitOfWork(Protocol):
    profiles: ProfileRepository

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
