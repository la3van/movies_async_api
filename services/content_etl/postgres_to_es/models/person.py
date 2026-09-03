"""Модели документов персон для Elasticsearch."""

from pydantic import BaseModel, ConfigDict, Field

from postgres_to_es.models.common import BaseDocument


class PersonMovie(BaseModel):
    """Фильм внутри документа персоны."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    roles: list[str] = Field(default_factory=list)


class PersonDocument(BaseDocument):
    """Документ персоны для индекса Elasticsearch."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    full_name: str
    films: list[PersonMovie] = Field(default_factory=list)
