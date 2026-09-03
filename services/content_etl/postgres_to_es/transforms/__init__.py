"""Функции трансформации данных PostgreSQL в документы Elasticsearch."""

from postgres_to_es.transforms.genres import transform_genre, transform_genres
from postgres_to_es.transforms.movies import transform_film, transform_films
from postgres_to_es.transforms.persons import (
    transform_person,
    transform_persons,
)

__all__ = (
    "transform_film",
    "transform_films",
    "transform_genre",
    "transform_genres",
    "transform_person",
    "transform_persons",
)
