"""Модуль бизнес-логики для работы с жанрами."""
from core.tracing import trace_method
from cache.base import Cache
from models.genre import Genre
from repositories.interfaces.genre import GenreRepository
from services.cache_keys.genres import (
    get_genre_cache_key,
    get_genres_cache_key,
)


class GenreService:
    """Сервис для получения информации о жанрах.

    Сервис управляет бизнес-сценариями получения жанров:
    проверяет кеш, обращается к основному хранилищу через репозиторий
    и сохраняет полученные результаты в кеш.
    """
    def __init__(
        self,
        repository: GenreRepository,
        cache: Cache,
        cache_ttl: int,
    ) -> None:
        """Инициализирует сервис жанров."""
        self._repository = repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    @trace_method("content.genres.get_by_id")
    async def get_genre_by_id(
        self,
        genre_id: str
    ) -> Genre | None:
        """Возвращает жанр по id
        или None, если жанр не найден."""
        genre_cache_key = get_genre_cache_key(genre_id)

        genre = await self._cache.get_model(
            key=genre_cache_key,
            model_type=Genre,
        )
        if genre is not None:
            return genre

        genre = await self._repository.get_by_id(genre_id)
        if genre is None:
            return None

        await self._cache.set_model(
            key=genre_cache_key,
            value=genre,
            ttl=self._cache_ttl,
        )

        return genre

    @trace_method("content.genres.get_many")
    async def get_genres(
        self,
        query: str | None = None,
        sort: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[Genre]:
        """Возвращает список жанров с учётом поиска, сортировки и пагинации."""
        normalized_query = query.strip() if query else None
        if not normalized_query:
            normalized_query = None

        effective_sort = sort
        if effective_sort is None and normalized_query is None:
            effective_sort = 'name'

        genres_cache_key = get_genres_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        genres = await self._cache.get_models(
            key=genres_cache_key,
            model_type=Genre,
        )
        if genres is not None:
            return genres

        genres = await self._repository.get_many(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await self._cache.set_models(
            key=genres_cache_key,
            values=genres,
            ttl=self._cache_ttl,
        )

        return genres
