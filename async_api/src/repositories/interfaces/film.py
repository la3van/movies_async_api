from abc import ABC, abstractmethod

from models.film import Film, ShortFilm


class FilmRepository(ABC):
    @abstractmethod
    async def get_by_id(self, film_id: str) -> Film | None:
        pass  # pragma: no cover

    @abstractmethod
    async def get_sorted(
        self,
        sort: str,
        genre_filter: str | None,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        pass  # pragma: no cover

    @abstractmethod
    async def search(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        pass  # pragma: no cover

    @abstractmethod
    async def find_similar_by_content_and_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        pass  # pragma: no cover

    @abstractmethod
    async def find_similar_by_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        pass  # pragma: no cover
