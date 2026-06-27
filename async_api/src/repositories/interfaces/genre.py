from abc import ABC, abstractmethod

from models.genre import Genre


class GenreRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self,
        genre_id: str,
    ) -> Genre | None:
        pass  # pragma: no cover

    @abstractmethod
    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Genre]:
        pass  # pragma: no cover
