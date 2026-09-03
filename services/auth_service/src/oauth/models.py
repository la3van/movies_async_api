"""Внутренние модели OAuth."""

from dataclasses import dataclass

from oauth.enums import OAuthProviderName
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True, slots=True)
class OAuthToken:
    """Токены, полученные от внешнего OAuth-провайдера."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    id_token: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthUserInfo:
    """Нормализованные данные пользователя OAuth-провайдера."""

    provider_user_id: str
    email: str | None = None
    email_verified: bool | None = None
    login: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationData:
    """Публичные параметры для начала OAuth-авторизации."""

    state: str
    code_challenge: str


class OAuthStateData(BaseModel):
    """Внутренние данные незавершённого OAuth-flow."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    provider: OAuthProviderName
    code_verifier: str = Field(
        min_length=43,
        max_length=128,
    )
    redirect_uri: str = Field(
        min_length=1,
    )
