"""Сервис работы с токенами."""
from core.tracing import trace_method
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.config import get_settings
from core.jwt import create_access_token
from core.security import generate_secure_token, hash_token
from models.user import User


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Пара access и refresh токенов."""
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


@dataclass(frozen=True, slots=True)
class RefreshTokenData:
    """Данные refresh-токена для сохранения refresh-сессии."""
    token: str
    token_hash: str
    expires_at: datetime


class TokenService:
    """Сервис создания access и refresh токенов."""
    def __init__(self) -> None:
        """Запоминаем настройки auth-сервиса."""
        self._settings = get_settings()

    @trace_method("tokens.create_access")
    def create_access_token_for_user(self, user: User) -> str:
        """Создаёт access-токен для пользователя."""
        roles = sorted(role.name for role in user.roles)

        permissions = sorted(
            {
                permission.code
                for role in user.roles
                for permission in role.permissions
            }
        )

        return create_access_token(
            subject=str(user.id),
            additional_claims={
                'login': user.login,
                'roles': roles,
                'permissions': permissions,
                'is_superuser': user.is_superuser,
            },
        )

    @trace_method("tokens.create_refresh")
    def create_refresh_token_data(self) -> RefreshTokenData:
        """Создаёт refresh-токен и данные для хранения в БД."""
        token = generate_secure_token()
        token_hash = hash_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self._settings.refresh_token_expire_days,
        )

        return RefreshTokenData(
            token=token,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    @trace_method("tokens.create_pair")
    def create_token_pair(
        self,
        user: User
    ) -> tuple[TokenPair, RefreshTokenData]:
        """Создаёт пару токенов и данные refresh-токена."""
        refresh_token_data = self.create_refresh_token_data()

        token_pair = TokenPair(
            access_token=self.create_access_token_for_user(user),
            refresh_token=refresh_token_data.token,
        )

        return token_pair, refresh_token_data
