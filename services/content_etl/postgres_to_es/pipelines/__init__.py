"""ETL-пайплайны фильмов, жанров и персон."""

from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.pipelines.films import FilmsPipeline
from postgres_to_es.pipelines.genres import GenresPipeline
from postgres_to_es.pipelines.persons import PersonsPipeline

__all__ = (
    "BasePipeline",
    "FilmsPipeline",
    "GenresPipeline",
    "PersonsPipeline",
)
