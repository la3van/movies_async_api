"""Модуль настроек auth-сервиса."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки auth-сервиса."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # Auth API project
    project_name: str = 'auth-service'
    debug: bool = False

    # Auth API
    auth_service_host: str = '0.0.0.0'
    auth_service_port: int = 8000

    # Postgres
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_db: str = 'auth'
    postgres_user: str = 'auth_user'
    postgres_password: str = 'auth_password'
    postgres_connect_timeout: int = 5
    postgres_statement_timeout_ms: int = 30000

    # Redis
    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_db: int = 2
    redis_key_prefix: str = 'auth'
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5
    redis_max_retries: int = 2
    redis_retry_backoff_base: float = 0.1
    redis_retry_backoff_cap: float = 1.0

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Superuser
    superuser_login: str = 'admin'
    superuser_password: str = 'admin_password'
    superuser_first_name: str = 'Admin'
    superuser_last_name: str = 'User'

    # Cache
    user_cache_expire_in_seconds: int = 300
    role_cache_expire_in_seconds: int = 300
    permission_cache_expire_in_seconds: int = 300
    token_claims_cache_expire_in_seconds: int = 300
    login_history_cache_expire_in_seconds: int = 60

    def build_redis_key(self, key: str) -> str:
        """Добавляет auth-префикс к Redis-ключу."""
        return f'{self.redis_key_prefix}:{key}'

    @property
    def postgres_url(self) -> str:
        """Возвращает url подключения к PostgreSQL."""
        return (
            f'postgresql+asyncpg://{self.postgres_user}:'
            f'{self.postgres_password}@{self.postgres_host}:'
            f'{self.postgres_port}/{self.postgres_db}'
        )

    def buil_redis_key(self, key: str) -> str:
        """Добавляет auth-префикс к Redis-ключу."""
        return f'{self.redis_key_prefix}:{key}'


@lru_cache()
def get_settings() -> Settings:
    """Возвращает настройки auth-сервиса."""
    return Settings()
