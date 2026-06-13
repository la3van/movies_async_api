"""Пакет с пайплайнами переноса данных по фильмам, жанрам и персонам"""
from postgres_to_es.pipelines.films import FilmsPipeline
from postgres_to_es.pipelines.genres import GenresPipeline
from postgres_to_es.pipelines.persons import PersonsPipeline

__all__ = (
    'FilmsPipeline',
    'GenresPipeline',
    'PersonsPipeline',
)
