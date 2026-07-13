"""Модели документов жанров для Elasticsearch."""
from pydantic import ConfigDict

from postgres_to_es.models.common import BaseDocument


class GenreDocument(BaseDocument):
    """Документ жанра для индекса Elasticsearch."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    name: str
    description: str | None = None
