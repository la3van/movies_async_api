"""Схемы API для фильмов."""
from uuid import UUID
from pydantic import BaseModel, Field


class ShortFilmResponse(BaseModel):
    """Краткая модель фильма для списков."""

    uuid: UUID = Field(
        description='Уникальный идентификатор фильма',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    title: str = Field(
        description='Название фильма',
        exmaples=['Spider-Man: Brand New Day'],
    )
    imdb_rating: float | None = Field(
        default=None,
        description='Рейтинг фильма',
        examples=[5.6, 9.1],
    )


class GenreInFilmResponse(BaseModel):
    """Жанр внутри полной информации о фильме."""

    uuid: UUID = Field(
        description='Уникальный идентификатор жанра',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    name: str = Field(
        description='Название жанра',
        exmples=['Action', 'Comedy'],
    )


class PersonInFilmResponse(BaseModel):
    """Персона внутри полной информации о фильме."""

    uuid: UUID = Field(
        description='Уникальный идентификатор персоны',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    full_name: str = Field(
        description='Имя персоны',
        examples=['Jason Stathem', 'Gal Gadot'],
    )


class FilmDetailResponse(BaseModel):
    """Полная модель фильма для страницы фильма."""

    uuid: UUID = Field(
        description='Уникальный идентификатор фильма',
        exmples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    title: str = Field(
        description='Название фильма',
        examples=['Spider-Man: Brand New Day'],
    )
    imdb_rating: float | None = Field(
        default=None,
        description='Рейтинг фильма',
        examples=[9.8, 5.1],
    )
    description: str | None = Field(
        default=None,
        description='Описание фильма',
        examples=[
            (
                'Один из лучших фильмов киностудии '
                'Marvel про человека паука'
            ),
        ],
    )
    genre: list[GenreInFilmResponse] = Field(
        description='Список жанров фильма',
    )
    actors: list[PersonInFilmResponse] = Field(
        description='Список актеров фильма',
    )
    writers: list[PersonInFilmResponse] = Field(
        description='Список сценаристов фильма',
    )
    directors: list[PersonInFilmResponse] = Field(
        description='Список режиссеров фильма',
    )
