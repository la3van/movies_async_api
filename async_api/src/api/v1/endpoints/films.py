"""Модуль с endpoint'ами для фильмов."""
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from services.film import FilmService, get_film_service

from api.v1.schemas.films import (
    ShortFilmResponse,
    FilmDetailResponse,
)
from api.v1.mappers.films import (
    build_film_detail_response,
    build_short_film_response,
)

router = APIRouter()


@router.get(
    '/',
    response_model=list[ShortFilmResponse],
    summary='Список фильмов',
    description=(
        'Возвращает список фильмов с пагинацией, сортировкой по рейтингу '
        'и опциональной фильтрацией по жанру.'
    ),
    response_description='Список фильмов с uuid, названием и рейтингом',
)
async def get_sorted_films(
    sort: str = Query(  # noqa: B008
        '-imdb_rating',
        pattern='^-?imdb_rating$',
        description=(
            'Поле сортировки. Для сортировки по убыванию используется '
            'префикс "-".'
        ),
        examples=['-imdb_rating'],
    ),
    genre: UUID | None = Query(  # noqa: B008
        None,
        description='UUID жанра для фильтрации фильмов',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    ),
    page_number: int = Query(  # noqa: B008
        1,
        ge=1,
        description='Номер страницы',
        examples=[1],
    ),
    page_size: int = Query(  # noqa: B008
        50,
        ge=1,
        le=100,
        description='Количество фильмов на странице',
        examples=[50],
    ),
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> list[ShortFilmResponse]:
    """Возвращает список фильмов с сортировкой, пагинацией и фильтром по
    жанру."""
    films = await film_service.get_sorted_films(
        sort=sort,
        genre_filter=str(genre) if genre else None,
        page_number=page_number,
        page_size=page_size,
    )

    return [
        build_short_film_response(film)
        for film in films
    ]


@router.get(
    '/search',
    response_model=list[ShortFilmResponse],
    summary='Поиск фильмов',
    description=(
        'Выполняет полнотекстовый поиск по фильмам. '
        'Поиск учитывает название, описание, актёров, сценаристов и'
        'режиссёров.'
    ),
    response_description='Список найденных фильмов',
)
async def search_films(
    query: str = Query(  # noqa: B008
        ...,
        min_length=1,
        description='Поисковая строка',
        examples=['star'],
    ),
    page_number: int = Query(  # noqa: B008
        1,
        ge=1,
        description='Номер страницы',
        examples=[1],
    ),
    page_size: int = Query(  # noqa: B008
        50,
        ge=1,
        le=100,
        description='Количество фильмов на странице',
        examples=[50],
    ),
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> list[ShortFilmResponse]:
    """Возвращает фильмы, найденные по поисковому запросу."""
    films = await film_service.get_searched_films(
        query=query,
        page_number=page_number,
        page_size=page_size,
    )

    return [
        build_short_film_response(film)
        for film in films
    ]


@router.get(
    '/{film_id}/similar',
    response_model=list[ShortFilmResponse],
    summary='Похожие фильмы',
    description=(
        'Возвращает фильмы, похожие на указанный фильм. '
        'Похожесть определяется через Elasticsearch more_like_this '
        'с дополнительным ограничением по жанрам.'
    ),
    response_description='Список похожих фильмов',
)
async def get_similar_films(
    film_id: UUID,
    page_number: int = Query(  # noqa: B008
        1,
        ge=1,
        description='Номер страницы',
        examples=[1],
    ),
    page_size: int = Query(  # noqa: B008
        50,
        ge=1,
        le=100,
        description='Количество фильмов на странице',
        examples=[10],
    ),
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> list[ShortFilmResponse]:
    """Возвращаем фильмы, похожие на указанный фильм."""
    films = await film_service.get_similar_films(
        film_id=str(film_id),
        page_number=page_number,
        page_size=page_size,
    )

    return [
        build_short_film_response(film)
        for film in films
    ]


@router.get(
    '/{film_id}',
    response_model=FilmDetailResponse,
    summary='Полная информация о фильме',
    description='Возвращает подробную информацию о фильме по его UUID.',
    response_description='Полная информация о фильме',
)
async def get_film(
    film_id: UUID,
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> FilmDetailResponse:
    """Возвращает полную информацию о фильме по id."""
    film = await film_service.get_film_by_id(str(film_id))

    if film is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='film_not_found',
        )

    return build_film_detail_response(film)
