"""Restricted legacy export contract, never exposed through Nginx."""

from uuid import UUID

from pydantic import BaseModel, Field


class LegacyProfile(BaseModel):
    user_id: UUID
    first_name: str | None
    last_name: str | None


class LegacyProfileBatch(BaseModel):
    items: list[LegacyProfile] = Field(max_length=100)
