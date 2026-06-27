# Functional tests

Функциональные тесты проверяют Async API через реальные HTTP-запросы в изолированном Docker Compose окружении.

## Что запускается

`tests/functional/docker-compose.yml` поднимает:

| Сервис | Назначение |
| --- | --- |
| `async_api` | Тестируемое FastAPI-приложение под coverage.py |
| `elasticsearch` | Изолированный Elasticsearch с тестовыми индексами |
| `redis` | Изолированный Redis для API-кеша |
| `tests` | Контейнер с pytest |

PostgreSQL и ETL в функциональных тестах не используются: тестовые Elasticsearch-документы создаются фикстурами напрямую.

## Структура

```text
tests/
├── functional/
│   ├── coverage/              # Coverage data и HTML-отчёт
│   ├── src/
│   │   ├── films/             # Тесты фильмов
│   │   ├── genres/            # Тесты жанров
│   │   ├── persons/           # Тесты персон
│   │   └── test_search.py     # Поиск по сущностям
│   ├── testdata/
│   │   ├── documents.py       # Генерация тестовых документов
│   │   └── responses.py       # Ожидаемые API-ответы
│   ├── utils/
│   │   ├── helpers.py
│   │   ├── wait_for_es.py
│   │   └── wait_for_redis.py
│   ├── conftest.py
│   ├── settings.py
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
└── README.md
```

## Покрываемые сценарии

### Films

- получение фильма по UUID;
- `404` для отсутствующего фильма;
- `422` для некорректного UUID;
- пагинация, сортировка и фильтрация по жанру;
- полнотекстовый поиск;
- похожие фильмы;
- отсутствие похожих фильмов;
- исходный фильм без жанров;
- получение одиночных и списочных результатов из Redis.

### Genres

- получение по UUID;
- список, поиск, сортировка и пагинация;
- пустой результат;
- `404` и `422`;
- чтение результата из кеша.

### Persons

- получение по UUID;
- поиск, сортировка и пагинация;
- фильмы персоны;
- `404` и `422`;
- чтение результатов из кеша.

## Подготовка окружения

Команды выполняются из каталога `tests/functional`:

```bash
cd tests/functional
```

Проверьте `.env`:

```env
ELASTIC_URL=http://elasticsearch:9200
REDIS_URL=redis://redis:6379/0
SERVICE_URL=http://async_api:8000
API_PREFIX=/api/v1
```

## Запуск всех тестов

```bash
docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests
```

Не прерывайте остановку Compose повторным `Ctrl+C`: coverage сохраняет данные при корректном завершении API-контейнера.

После завершения можно удалить тестовые контейнеры:

```bash
docker compose down -v
```

## Запуск отдельного файла или теста

Сначала при необходимости поднимите зависимости либо используйте `docker compose run`:

```bash
docker compose run --rm tests \
  pytest -v tests/functional/src/films/test_films.py
```

```bash
docker compose run --rm tests \
  pytest -v \
  tests/functional/src/films/test_films.py::test_get_film_by_id
```

После изменения кода Async API пересоберите его образ:

```bash
docker compose up --build --force-recreate \
  --abort-on-container-exit \
  --exit-code-from tests
```

## Coverage

Файл покрытия сохраняется на хосте в:

```text
tests/functional/coverage/.coverage
```

Текстовый отчёт:

```bash
docker compose run --rm --no-deps async_api \
  coverage report -m
```

HTML-отчёт:

```bash
docker compose run --rm --no-deps async_api \
  coverage html -d /coverage/htmlcov
```

Открыть на macOS:

```bash
open coverage/htmlcov/index.html
```

Coverage здесь отражает строки Async API, выполненные функциональными HTTP-тестами. Защитные ветки инициализации/закрытия клиентов удобнее проверять отдельными unit-тестами.

## Изоляция данных

Фикстура `es_write_data` пересоздаёт индекс перед загрузкой документов. Redis очищается до и после каждого теста.

Тесты кеша работают по схеме:

1. первый запрос заполняет Redis;
2. документ удаляется из Elasticsearch;
3. повторный запрос должен вернуть прежний результат из кеша.

## Проверка типов

Основной production-код полностью аннотирован. В функциональных тестах часть fixture и `test_*` функций пока не имеет аннотаций; рекомендуемые типы перечислены в итогах аудита.
