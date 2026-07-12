"""Настройки функциональных тестов auth-сервиса."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Настройки функциональных тестов auth-сервиса."""
    model_config = SettingsConfigDict(
        env_file='tests/functional/.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    service_url: str = 'http://auth-service:8000'
    api_prefix: str = 'api/v1'
    http_request_timeout: int = 10

    postgres_host: str = 'auth-postgres'
    postgres_port: int = 5432
    postgres_db: str = 'auth_test'
    postgres_user: str = 'auth_user'
    postgres_password: str = 'auth_password'
    postgres_connect_timeout: int = 5

    redis_host: str = 'redis'
    redis_port: int = 6379
    redis_db: int = 0
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5

    wait_attempts: int = 30
    wait_sleep_seconds: int = 1

    def get_redis_url(self) -> str:
        """Возвращает DSN подключения к Redis."""
        return (
            f'redis://{self.redis_host}:'
            f'{self.redis_port}/{self.redis_db}'
        )


@lru_cache
def get_test_settings() -> TestSettings:
    """Возвращает закешированные настройки функциональных тестов."""
    return TestSettings()


test_settings = get_test_settings()
