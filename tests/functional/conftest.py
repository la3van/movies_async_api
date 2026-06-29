"""Подключение фикстур функциональных тестов."""
pytest_plugins = (
    'tests.functional.testdata.genres',
    'tests.functional.testdata.persons',
    'tests.functional.testdata.films',
    'tests.functional.fixtures.common',
    'tests.functional.fixtures.elastic',
    'tests.functional.fixtures.redis',
    'tests.functional.fixtures.http',
    'tests.functional.fixtures.genres',
    'tests.functional.fixtures.persons',
    'tests.functional.fixtures.films',
)
