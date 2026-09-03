"""Модуль настроек auth-сервиса."""

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки auth-сервиса."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth API project
    project_name: str = "auth-service"
    debug: bool = False

    # Auth API
    auth_service_host: str = "0.0.0.0"
    auth_service_port: int = 8000

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "auth"
    postgres_user: str = "auth_user"
    postgres_password: str = "auth_password"
    postgres_connect_timeout: int = 5
    postgres_statement_timeout_ms: int = 30000

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 2
    redis_key_prefix: str = "auth"
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5
    redis_max_retries: int = 2
    redis_retry_backoff_base: float = 0.1
    redis_retry_backoff_cap: float = 1.0

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_key_prefix: str = "auth:rate_limit"

    # Trusted reverse proxies
    trusted_proxy_sources: str = "nginx,admin-service"

    # OAuth
    oauth_state_ttl_seconds: int = 300
    oauth_state_key_prefix: str = "oauth:state"

    # OAuth HTTP
    oauth_http_timeout_seconds: int = 10

    # Yandex OAuth
    yandex_oauth_client_id: str = ""
    yandex_oauth_client_secret: SecretStr = SecretStr("")
    yandex_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/oauth/yandex/callback"
    )
    yandex_oauth_scopes: str = "login:info login:email"

    # Google OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: SecretStr = SecretStr("")
    google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/oauth/google/callback"
    )
    google_oauth_scopes: str = "openid email profile"

    # TODO: Complete VK ID end-to-end setup after obtaining
    # a trusted public HTTPS domain. VK ID rejects localhost
    # and temporary trycloudflare.com callback domains.
    vk_oauth_client_id: str = ""
    vk_oauth_redirect_uri: str = ""
    vk_oauth_scopes: str = "email"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Access token revocation
    access_token_revocation_key_prefix: str = "access_tokens:revoked"
    access_token_revocation_clock_skew_seconds: int = 30

    # Superuser
    superuser_login: str = "admin"
    superuser_email: str = "admin@example.com"
    superuser_password: SecretStr
    superuser_first_name: str = "Admin"
    superuser_last_name: str = "User"

    # Cache
    user_cache_expire_in_seconds: int = 300
    role_cache_expire_in_seconds: int = 300
    permission_cache_expire_in_seconds: int = 300
    token_claims_cache_expire_in_seconds: int = 300
    login_history_cache_expire_in_seconds: int = 60

    @field_validator(
        "jwt_secret_key",
        "superuser_password",
    )
    @classmethod
    def validate_required_secret(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """Запрещает пустые и заведомо небезопасные секреты."""
        secret = value.get_secret_value().strip()

        if not secret:
            raise ValueError(
                "Secret value must not be empty",
            )

        forbidden_values = {
            "generate_me",
            "admin_password",
            "change_me",
            "your_secret",
        }

        if secret in forbidden_values:
            raise ValueError(
                "Replace the insecure example secret",
            )
        return value

    def build_redis_key(self, key: str) -> str:
        """Добавляет auth-префикс к Redis-ключу."""
        return f"{self.redis_key_prefix}:{key}"

    @property
    def postgres_url(self) -> str:
        """Возвращает url подключения к PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Возвращает настройки auth-сервиса."""
    return Settings()
