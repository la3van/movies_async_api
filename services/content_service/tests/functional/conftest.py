"""Подключение фикстур функциональных тестов."""

pytest_plugins = (
    "tests.functional.test_data.genres",
    "tests.functional.test_data.persons",
    "tests.functional.test_data.films",
    "tests.functional.fixtures.common",
    "tests.functional.fixtures.elastic",
    "tests.functional.fixtures.redis",
    "tests.functional.fixtures.http",
    "tests.functional.fixtures.genres",
    "tests.functional.fixtures.persons",
    "tests.functional.fixtures.films",
)
