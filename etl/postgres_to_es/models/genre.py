"""Модели документов жанров для Elasticsearch."""
from pydantic import BaseModel, ConfigDict


class GenreDocument(BaseModel):
    """Документ жанра для индекса Elasticsearch."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    name: str
    description: str | None = None
