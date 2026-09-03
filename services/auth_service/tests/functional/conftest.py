"""Подключение фикстур функциональных тестов auth-сервиса."""

pytest_plugins = (
    "tests.functional.fixtures.common",
    "tests.functional.fixtures.http",
    "tests.functional.fixtures.postgres",
    "tests.functional.fixtures.redis",
    "tests.functional.fixtures.auth",
)
