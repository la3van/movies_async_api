"""Общие модели ETl."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChangedRecord(BaseModel):
    """Запись с идентификатором и временем изменения."""
    model_config = ConfigDict(extra='forbid')

    id: str
    modified: datetime | str


class BaseDocument(BaseModel):
    """Базовая модель документа целевого хранилища."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
