"""Модуль с endpoint'ами для жанров."""
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from services.genre import GenreService, get_genre_service

from api.v1.schemas.genres import GenreResponse
from api.v1.mappers.genres import build_genre_response

router = APIRouter()


@router.get(
    '/',
    response_model=list[GenreResponse],
    summary='Список жанров',
    description=(
        'Возвращает список жанров с пагинацией, опциональным поиском '
        'по названию и описанию, а также сортировкой по названию.'
    ),
    response_description='Список жанров с uuid и названием',
)
async def get_genres(
    query: str | None = Query(  # noqa: B008
        None,
        min_length=1,
        description='Поисковая строка для фильтрации жанров',
        examples=['action'],
    ),
    sort: str | None = Query(  # noqa: B008
        None,
        pattern='^-?name$',
        description='Поле сортировки. Для убывания используется префикс "-".',
        examples=['name'],
    ),
    page_number: int = Query(  # noqa: B008
        1,
        ge=1,
        description='Номер страницы',
    ),
    page_size: int = Query(  # noqa: B008
        50,
        ge=1,
        le=100,
        description='Количество жанров на странице',
    ),
    genre_service: GenreService = Depends(get_genre_service),  # noqa: B008
) -> list[GenreResponse]:
    """Возвращает список жанров."""
    genres = await genre_service.get_genres(
        query=query,
        sort=sort,
        page_number=page_number,
        page_size=page_size,
    )

    return [
        build_genre_response(genre)
        for genre in genres
    ]


@router.get(
    '/{genre_id}',
    response_model=GenreResponse,
    summary='Информация о жанре',
    description='Возвращает информацию о жанре по его UUID.',
    response_description='Информация о жанре',
)
async def get_genre(
    genre_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),  # noqa: B008
) -> GenreResponse:
    """Возвращает жанр по id."""
    genre = await genre_service.get_genre_by_id(str(genre_id))

    if genre is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='genre_not_found',
        )

    return build_genre_response(genre)
