"""Публичные интерфейсы ETL-приложения."""

from postgres_to_es.interfaces.connection import ConnectionProvider
from postgres_to_es.interfaces.loader import DocumentLoader
from postgres_to_es.interfaces.retry import RetryExecutor
from postgres_to_es.interfaces.sources import (
    FilmsSource,
    GenresSource,
    PersonsSource,
)

__all__ = (
    "ConnectionProvider",
    "DocumentLoader",
    "FilmsSource",
    "GenresSource",
    "PersonsSource",
    "RetryExecutor",
)
