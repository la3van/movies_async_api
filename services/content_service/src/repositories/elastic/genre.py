"""Реализация репозитория жанров через Elasticsearch."""
from elasticsearch import AsyncElasticsearch, NotFoundError

from models.genre import Genre
from repositories.elastic.bodies.genres import (
    build_genres_body,
)
from repositories.interfaces.genre import GenreRepository


class ElasticsearchGenreRepository(GenreRepository):
    """Репозиторий жанров, использующий Elasticsearch."""
    def __init__(
        self,
        elastic: AsyncElasticsearch,
        index_name: str,
        genre_sort_fields: dict[str, str],
    ) -> None:
        """Инициализирует репозиторий жанров."""
        self._elastic = elastic
        self._index_name = index_name
        self._genre_sort_fields = genre_sort_fields

    async def get_by_id(
        self,
        genre_id: str,
    ) -> Genre | None:
        """Возвращает жанр по идентификатору или None, если жанр не найден."""
        try:
            document = await self._elastic.get(
                index=self._index_name,
                id=genre_id,
            )
        except NotFoundError:
            return None

        return Genre.model_validate(document['_source'])

    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Genre]:
        """Возвращает страницу жанров с учётом поиска и сортировки."""
        body = build_genres_body(
            query=query,
            sort=sort,
            page_number=page_number,
            page_size=page_size,
            genre_sort_fields=self._genre_sort_fields,
        )

        response = await self._elastic.search(
            index=self._index_name,
            body=body,
        )

        return [
            Genre.model_validate(hit['_source'])
            for hit in response['hits']['hits']
        ]
