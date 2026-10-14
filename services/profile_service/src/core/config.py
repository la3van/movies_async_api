"""Validated configuration; secrets are never included in API errors."""

import base64
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    project_name: str = "profile-service"
    postgres_host: str = "profile-postgres"
    postgres_port: int = 5432
    postgres_db: str = "profiles"
    postgres_user: str = "profile_user"
    postgres_password: SecretStr
    database_url: str = ""
    auth_base_url: str = "http://auth-service:8000/api/v1/"
    http_timeout_seconds: float = Field(default=5, gt=0, le=30)
    encryption_keys: SecretStr
    phone_index_key: SecretStr
    notification_token: SecretStr
    migration_token: SecretStr

    @field_validator("encryption_keys", "phone_index_key")
    @classmethod
    def valid_keys(cls, value: SecretStr) -> SecretStr:
        try:
            keys = value.get_secret_value().split(",")
            for key in keys:
                if (
                    len(
                        base64.b64decode(
                            key.strip(), altchars=b"-_", validate=True
                        )
                    )
                    != 32
                ):
                    raise ValueError
        except (ValueError, TypeError) as exc:
            raise ValueError("Expected base64-encoded 32-byte keys") from exc
        return value

    @field_validator("notification_token", "migration_token")
    @classmethod
    def valid_token(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("Service tokens must contain at least 32 chars")
        return value

    @field_validator("phone_index_key")
    @classmethod
    def single_index_key(cls, value: SecretStr) -> SecretStr:
        if "," in value.get_secret_value():
            raise ValueError("PHONE_INDEX_KEY must contain exactly one key")
        return value

    @property
    def postgres_url(self) -> str:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
