"""Модуль с router'ом, моделями ответа API и обработчиками персон."""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models.film import ShortFilm
from models.person import Person, PersonFilm
from services.person import PersonService, get_person_service

router = APIRouter()


class PersonFilmResponse(BaseModel):
    """Фильм внутри информации о персоне."""

    uuid: UUID
    roles: list[str]


class PersonResponse(BaseModel):
    """Модель ответа API для персоны."""

    uuid: UUID
    full_name: str
    films: list[PersonFilmResponse]


class ShortFilmResponse(BaseModel):
    """Краткая модель фильма для списков."""

    uuid: UUID
    title: str
    imdb_rating: float | None


def build_person_film_response(film: PersonFilm) -> PersonFilmResponse:
    """Собирает ответ API для фильма внутри персоны."""
    return PersonFilmResponse(
        uuid=UUID(film.uuid),
        roles=film.roles,
    )


def build_person_response(person: Person) -> PersonResponse:
    """Собирает ответ API для персоны."""
    return PersonResponse(
        uuid=UUID(person.uuid),
        full_name=person.full_name,
        films=[
            build_person_film_response(film)
            for film in person.films
        ],
    )


def build_short_film_response(film: ShortFilm) -> ShortFilmResponse:
    """Собирает краткий ответ API для фильма."""
    return ShortFilmResponse(
        uuid=UUID(film.uuid),
        title=film.title,
        imdb_rating=film.imdb_rating,
    )


@router.get(
    '/search',
    response_model=list[PersonResponse],
    summary='Поиск персон',
    description=(
        'Выполняет поиск персон по имени. '
        'Возвращает найденных актёров, режиссёров и сценаристов '
        'со списком связанных фильмов и ролей.'
    ),
    response_description='Список найденных персон',
)
async def search_persons(
    query: str = Query(  # noqa: B008
        ...,
        min_length=1,
        description='Поисковая строка для поиска персон',
        examples=['captain'],
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
        description='Количество персон на странице',
    ),
    person_service: PersonService = Depends(get_person_service),  # noqa: B008
) -> list[PersonResponse]:
    """Возвращает персон, найденных по поисковому запросу."""
    persons = await person_service.get_persons(
        query=query,
        page_number=page_number,
        page_size=page_size,
    )

    return [
        build_person_response(person)
        for person in persons
    ]


@router.get(
    '/{person_id}/film',
    response_model=list[ShortFilmResponse],
    summary='Фильмы персоны',
    description=(
        'Возвращает фильмы, связанные с указанной персоной. '
        'Персона может быть актёром, режиссёром или сценаристом фильма.'
    ),
    response_description='Список фильмов персоны',
)
async def get_person_films(
    person_id: UUID,
    page_number: int = Query(  # noqa: B008
        1,
        ge=1,
        description='Номер страницы',
    ),
    page_size: int = Query(  # noqa: B008
        50,
        ge=1,
        le=100,
        description='Количество фильмов на странице',
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
            detail='person_not_found',
        )

    return [
        build_short_film_response(film)
        for film in films
    ]


@router.get(
    '/{person_id}',
    response_model=PersonResponse,
    summary='Информация о персоне',
    description=(
        'Возвращает информацию о персоне по её UUID: '
        'имя и список фильмов, в которых она участвовала.'
    ),
    response_description='Информация о персоне',
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
            detail='person_not_found',
        )

    return build_person_response(person)
