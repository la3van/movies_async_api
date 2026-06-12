"""Общие модели ETl."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChangedRecord(BaseModel):
    """Запись с идентификатором и временем изменения."""
    model_config = ConfigDict(extra='forbid')

    id: str
    modified: datetime | str
