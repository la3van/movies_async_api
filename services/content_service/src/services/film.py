"""Модуль бизнес-логики для работы с фильмами."""
from cache.base import Cache
from models.film import Film, ShortFilm
from repositories.interfaces.film import FilmRepository
from services.cache_keys.films import (
    get_film_cache_key,
    get_searched_films_cache_key,
    get_similar_films_cache_key,
    get_sorted_films_cache_key,
)


class FilmService:
    """Сервис для получения информации о фильмах.

    Сервис управляет бизнес-сценариями получения фильмов:
    проверяет кеш, обращается к основному хранилищу через репозиторий
    и сохраняет полученные результаты в кеш.
    """
    def __init__(
        self,
        repository: FilmRepository,
        cache: Cache,
        cache_ttl: int,
    ) -> None:
        """Инициализирует сервис фильмов."""
        self._repository = repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    async def get_film_by_id(
        self,
        film_id: str
    ) -> Film | None:
        """Возвращает фильм по id или None, если фильм не найден."""
        film_cache_key = get_film_cache_key(film_id)

        film = await self._cache.get_model(
            key=film_cache_key,
            model_type=Film,
        )
        if film is not None:
            return film

        film = await self._repository.get_by_id(film_id)
        if film is None:
            return None

        await self._cache.set_model(
            key=film_cache_key,
            value=film,
            ttl=self._cache_ttl,
        )

        return film

    async def get_sorted_films(
        self,
        sort: str = '-imdb_rating',
        genre_filter: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[ShortFilm]:
        """Возвращает список фильмов с сортировкой, пагинацией и фильтром по
        жанру."""
        sorted_films_cache_key = get_sorted_films_cache_key(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )

        sorted_films = await self._cache.get_models(
            key=sorted_films_cache_key,
            model_type=ShortFilm,
        )
        if sorted_films is not None:
            return sorted_films

        sorted_films = await self._repository.get_sorted(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )
        await self._cache.set_models(
            key=sorted_films_cache_key,
            values=sorted_films,
            ttl=self._cache_ttl,
        )

        return sorted_films

    async def get_searched_films(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает фильмы, найденные по поисковому
        запросу."""
        searched_films_cache_key = get_searched_films_cache_key(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

        searched_films = await self._cache.get_models(
            key=searched_films_cache_key,
            model_type=ShortFilm,
        )
        if searched_films is not None:
            return searched_films

        searched_films = await self._repository.search(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )
        await self._cache.set_models(
            key=searched_films_cache_key,
            values=searched_films,
            ttl=self._cache_ttl,
        )

        return searched_films

    async def get_similar_films(
        self,
        film_id: str,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[ShortFilm] | None:
        """Возвращает фильмы, похожие на указанный фильм."""
        similar_films_cache_key = get_similar_films_cache_key(
            film_id=film_id,
            page_number=page_number,
            page_size=page_size,
        )

        similar_films = await self._cache.get_models(
            key=similar_films_cache_key,
            model_type=ShortFilm,
        )
        if similar_films is not None:
            return similar_films

        film = await self.get_film_by_id(film_id)

        if film is None:
            return None

        genre_uuids = [
            genre.uuid
            for genre in film.genre
        ]
        if not genre_uuids:
            return []

        similar_films = (
            await self._repository.find_similar_by_content_and_genres(
                film_id=film_id,
                genre_uuids=genre_uuids,
                page_number=page_number,
                page_size=page_size,
            )
        )

        if not similar_films:
            similar_films = await self._repository.find_similar_by_genres(
                film_id=film_id,
                genre_uuids=genre_uuids,
                page_number=page_number,
                page_size=page_size,
            )

        await self._cache.set_models(
            key=similar_films_cache_key,
            values=similar_films,
            ttl=self._cache_ttl,
        )

        return similar_films
