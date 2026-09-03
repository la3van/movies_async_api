"""Модуль с endpoint'ами для персон."""

from http import HTTPStatus
from uuid import UUID

from api.dependencies import get_person_service
from api.v1.mappers.persons import (
    build_person_response,
    build_short_film_response,
)
from api.v1.schemas.films import ShortFilmResponse
from api.v1.schemas.persons import PersonResponse
from core.rate_limit import rate_limit
from fastapi import APIRouter, Depends, HTTPException, Query
from services.person import PersonService

router = APIRouter()


@router.get(
    "/search",
    response_model=list[PersonResponse],
    dependencies=[
        Depends(
            rate_limit(
                scope="persons:search",
                requests=30,
                window_seconds=60,
            ),
        ),
    ],
    summary="Поиск персон",
    description=(
        "Выполняет поиск персон по имени. "
        "Возвращает найденных актёров, режиссёров и сценаристов "
        "со списком связанных фильмов и ролей."
    ),
    response_description="Список найденных персон",
)
async def search_persons(
    query: str | None = Query(
        None,
        min_length=1,
        description="Поисковая строка для поиска персон",
        examples=["captain"],
    ),
    sort: str | None = Query(
        None,
        pattern="^-?full_name$",
        description='Поле сортировки. Для убывания используется префикс "-".',
        examples=["full_name"],
    ),
    page_number: int = Query(
        1,
        ge=1,
        description="Номер страницы",
    ),
    page_size: int = Query(
        50,
        ge=1,
        le=100,
        description="Количество персон на странице",
    ),
    person_service: PersonService = Depends(get_person_service),  # noqa: B008
) -> list[PersonResponse]:
    """Возвращает персон, найденных по поисковому запросу."""
    persons = await person_service.get_persons(
        query=query,
        sort=sort,
        page_number=page_number,
        page_size=page_size,
    )

    return [build_person_response(person) for person in persons]


@router.get(
    "/{person_id}/films",
    response_model=list[ShortFilmResponse],
    summary="Фильмы персоны",
    description=(
        "Возвращает фильмы, связанные с указанной персоной. "
        "Персона может быть актёром, режиссёром или сценаристом фильма."
    ),
    response_description="Список фильмов персоны",
    responses={
        404: {
            "description": "Персона не найдена",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "person_not_found",
                    },
                },
            },
        },
    },
)
async def get_person_films(
    person_id: UUID,
    page_number: int = Query(
        1,
        ge=1,
        description="Номер страницы",
    ),
    page_size: int = Query(
        50,
        ge=1,
        le=100,
        description="Количество фильмов на странице",
    ),
    person_service: PersonService = Depends(get_person_service),  # noqa: B008
) -> list[ShortFilmResponse]:
    """Возвращает фильмы, связанные с персоной."""
    films = await person_service.get_person_films(
        person_id=str(person_id),
        page_number=page_number,
        page_size=page_size,
    )

    if films is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="person_not_found",
        )

    return [build_short_film_response(film) for film in films]


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Информация о персоне",
    description=(
        "Возвращает информацию о персоне по её UUID: "
        "имя и список фильмов, в которых она участвовала."
    ),
    response_description="Информация о персоне",
    responses={
        404: {
            "description": "Персона не найдена",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "person_not_found",
                    },
                },
            },
        },
    },
)
async def get_person(
    person_id: UUID,
    person_service: PersonService = Depends(get_person_service),  # noqa: B008
) -> PersonResponse:
    """Возвращает персону по id."""
    person = await person_service.get_person_by_id(str(person_id))

    if person is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="person_not_found",
        )

    return build_person_response(person)
