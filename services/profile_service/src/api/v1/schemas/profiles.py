"""Separate private profile and restricted notification contracts."""

from datetime import datetime
from uuid import UUID

from core.security import normalize_phone
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=64)
    marketing_consent: bool = False

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None


class ProfileCreate(ProfileFields):
    pass


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=64)
    marketing_consent: bool | None = None

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None

    @model_validator(mode="after")
    def nonempty(self) -> "ProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for name in ("first_name", "last_name", "marketing_consent"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ProfileResponse(BaseModel):
    user_id: UUID
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    phone: str | None
    phone_verified_at: datetime | None
    marketing_consent: bool
    created_at: datetime
    updated_at: datetime


class ProfilePage(BaseModel):
    items: list[ProfileResponse]
    next_cursor: UUID | None = None


class NotificationName(BaseModel):
    user_id: UUID
    first_name: str | None
    last_name: str | None
