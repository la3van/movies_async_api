"""Схемы ответов API пользовательских событий."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class EventAcceptedResponse(BaseModel):
    """Ответ об успешном приёме пользовательского события."""

    event_id: UUID
    status: Literal["accepted"] = "accepted"
