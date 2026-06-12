"""Модуль с описанием Pydantic модели жанра."""
from pydantic import BaseModel, ConfigDict


class Genre(BaseModel):
    """Схема жанра из Elasticsearch."""
    model_config = ConfigDict(extra='forbid')

    uuid: str  # noqa: A003, VNE003
    name: str
    description: str | None = None
