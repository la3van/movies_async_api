"""Реализации загрузчиков документов."""
from postgres_to_es.loaders.elastic import ElasticsearchLoader

__all__ = (
    'ElasticsearchLoader',
)
