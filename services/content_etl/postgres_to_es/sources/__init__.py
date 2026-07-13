"""Реализации источников данных ETL."""
from postgres_to_es.sources.postgres import PostgresSource

__all__ = (
    'PostgresSource',
)
