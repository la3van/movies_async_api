"""Реализация репозитория фильмов через Elasticsearch."""
from elasticsearch import AsyncElasticsearch, NotFoundError

from models.film import Film, ShortFilm
from repositories.elastic.bodies.films import (
    build_searched_films_body,
    build_similar_films_body,
    build_sorted_films_body,
)
from repositories.elastic.mappers.films import build_short_film
from repositories.interfaces.film import FilmRepository


class ElasticsearchFilmRepository(FilmRepository):
    """Репозиторий фильмов, использующий Elasticsearch."""
    def __init__(
        self,
        elastic: AsyncElasticsearch,
        index_name: str,
        film_sort_fields: dict[str, str],
    ) -> None:
        """Инициализирует репозиторий фильмов."""
        self._elastic = elastic
        self._index_name = index_name
        self._film_sort_fields = film_sort_fields

    async def get_by_id(
        self,
        film_id: str,
    ) -> Film | None:
        """Возвращает фильм по идентификатору или None,
        если фильм не найден."""
        try:
            document = await self._elastic.get(
                index=self._index_name,
                id=film_id,
            )
        except NotFoundError:
            return None

        return Film.model_validate(document["_source"])

    async def get_sorted(
        self,
        sort: str,
        genre_filter: str | None,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает отсортированный список фильмов."""
        body = build_sorted_films_body(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
            film_sort_fields=self._film_sort_fields,
        )

        response = await self._elastic.search(
            index=self._index_name,
            body=body,
        )

        return [
            build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def search(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет фильмы по текстовому запросу."""
        body = build_searched_films_body(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

        response = await self._elastic.search(
            index=self._index_name,
            body=body,
        )

        return [
            build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def find_similar_by_content_and_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает похожие фильмы.

        Похожесть определяется по жанрам и more_like_this
        из Elasticsearch query."""
        body = build_similar_films_body(
            use_more_like_this=True,
            film_id=film_id,
            genre_uuids=genre_uuids,
            page_number=page_number,
            page_size=page_size,
            index_name=self._index_name,
        )

        response = await self._elastic.search(
            index=self._index_name,
            body=body,
        )

        return [
            build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def find_similar_by_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает похожие фильмы.

        Похожесть определяется только по наличию общих жанров."""
        body = build_similar_films_body(
            use_more_like_this=False,
            film_id=film_id,
            genre_uuids=genre_uuids,
            page_number=page_number,
            page_size=page_size,
            index_name=self._index_name,
        )

        response = await self._elastic.search(
            index=self._index_name,
            body=body,
        )

        return [
            build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]
