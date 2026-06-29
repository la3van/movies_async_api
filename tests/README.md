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
│   ├── coverage/                      # Coverage data и HTML-отчёт
│   ├── fixtures/
│   │   ├── common.py                  # event loop и общие фикстуры
│   │   ├── elastic.py                 # Elasticsearch client и операции с индексами
│   │   ├── redis.py                   # Redis client и очистка кеша
│   │   ├── http.py                    # aiohttp session и фабрика GET-запросов
│   │   ├── films.py                   # загрузка тестовых фильмов
│   │   ├── genres.py                  # загрузка тестовых жанров
│   │   └── persons.py                 # загрузка тестовых персон
│   ├── src/
│   │   ├── films/
│   │   │   ├── test_film_detail.py    # GET /films/{film_id}
│   │   │   ├── test_film_list.py      # GET /films/
│   │   │   ├── test_film_search.py    # GET /films/search
│   │   │   └── test_film_similar.py   # GET /films/{film_id}/similar
│   │   ├── genres/
│   │   │   ├── test_genre_detail.py   # GET /genres/{genre_id}
│   │   │   └── test_genre_list.py     # GET /genres/
│   │   └── persons/
│   │       ├── test_person_detail.py  # GET /persons/{person_id}
│   │       ├── test_person_films.py   # GET /persons/{person_id}/films
│   │       └── test_person_search.py  # GET /persons/search
│   ├── testdata/
│   │   ├── films.py                   # документы фильмов и similar-сценарии
│   │   ├── genres.py                  # документы жанров
│   │   ├── persons.py                 # документы персон
│   │   └── responses.py               # построение ожидаемых API-ответов
│   ├── utils/
│   │   ├── helpers.py
│   │   ├── wait_for_es.py
│   │   └── wait_for_redis.py
│   ├── conftest.py                    # регистрация fixture-модулей через pytest_plugins
│   ├── settings.py
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
└── README.md
```

Тестовые файлы организованы по endpoint. Для каждого endpoint сначала расположены успешные сценарии, затем проверка Redis-кеша, после неё — `404` и ошибки валидации.

## Организация фикстур

Корневой `conftest.py` регистрирует модули через `pytest_plugins`. Тестовые файлы не импортируют фикстуры напрямую: pytest разрешает зависимости по именам аргументов.

Фикстуры разделены на:

- инфраструктурные: HTTP, Elasticsearch, Redis и event loop;
- предметные: загрузка films, genres и persons;
- тестовые документы: отдельные генераторы для каждого индекса.

Фикстура `es_write_data` пересоздаёт индекс перед загрузкой документов. Redis очищается до и после каждого теста.

## Покрываемые сценарии

### Films

- получение фильма по UUID;
- фильм с пустыми optional-полями и без связей;
- `404` для отсутствующего фильма;
- `422` для некорректного UUID;
- минимальное и максимальное значения пагинации;
- страница после последней;
- сортировка и фильтрация по жанру;
- корректный UUID жанра без совпадений;
- полнотекстовый поиск по названию, описанию и именам участников;
- пустой и отсутствующий обязательный `query`;
- похожие фильмы по содержанию и жанрам;
- fallback-поиск похожих фильмов по жанрам;
- отсутствие похожих фильмов;
- исходный фильм без жанров;
- пагинация похожих фильмов;
- получение одиночных и списочных результатов из Redis;
- ошибки формата query-параметров и неподдерживаемая сортировка.

### Genres

- получение по UUID;
- список без поискового запроса;
- поиск, сортировка и пагинация;
- минимальный и максимальный `page_size`;
- страница после последней;
- пустой `query`;
- пустой результат поиска;
- `404` и `422`;
- неподдерживаемая сортировка;
- ошибки формата query-параметров;
- чтение результата из кеша.

### Persons

- получение по UUID;
- поиск, сортировка и пагинация;
- минимальный и максимальный `page_size`;
- страница после последней;
- пустой `query`;
- фильмы персоны;
- существующая персона без связанных фильмов;
- `404` и `422`;
- неподдерживаемая сортировка;
- ошибки формата query-параметров;
- чтение результатов из кеша.

## Подготовка окружения

Команды выполняются из каталога `tests/functional`:

```bash
cd tests/functional
```

Проверьте `.env`:

```env
ELASTIC_URL=http://elasticsearch:9200
REDIS_URL=redis://redis:6379/1
SERVICE_URL=http://async_api:8000
API_PREFIX=/api/v1
```

Тестовый Redis-клиент должен использовать ту же базу, что и Async API, чтобы autouse-фикстура действительно очищала кеш приложения.

## Запуск всех тестов

```bash
docker compose up --build   --abort-on-container-exit   --exit-code-from tests
```

Не прерывайте остановку Compose повторным `Ctrl+C`: coverage сохраняет данные при корректном завершении API-контейнера.

После завершения можно удалить тестовые контейнеры:

```bash
docker compose down -v
```

## Запуск отдельной группы, файла или теста

Запуск всех тестов фильмов:

```bash
docker compose run --rm tests   pytest -v tests/functional/src/films
```

Запуск одного endpoint-файла:

```bash
docker compose run --rm tests   pytest -v tests/functional/src/films/test_film_similar.py
```

Запуск одного теста:

```bash
docker compose run --rm tests   pytest -v   tests/functional/src/films/test_film_detail.py::test_get_film_by_id
```

После изменения кода Async API пересоберите его образ:

```bash
docker compose up --build --force-recreate   --abort-on-container-exit   --exit-code-from tests
```

## Coverage

Файл покрытия сохраняется на хосте в:

```text
tests/functional/coverage/.coverage
```

Текстовый отчёт:

```bash
docker compose run --rm --no-deps async_api   coverage report -m
```

HTML-отчёт:

```bash
docker compose run --rm --no-deps async_api   coverage html -d /coverage/htmlcov
```

Открыть на macOS:

```bash
open coverage/htmlcov/index.html
```

Coverage здесь отражает строки Async API, выполненные функциональными HTTP-тестами. Защитные ветки инициализации и закрытия клиентов удобнее проверять отдельными unit-тестами.

## Изоляция данных и проверка кеша

Тесты кеша работают по схеме:

1. первый запрос заполняет Redis;
2. документ удаляется из Elasticsearch;
3. повторный запрос должен вернуть прежний результат из кеша.

Отдельные наборы документов используются для предсказуемой проверки `more_like_this`, fallback-поиска по жанрам и сценариев без совпадений.

## Maintainability Index

Проверка выполняется из корня проекта:

```bash
radon mi tests/functional -s
```

Все файлы функциональных тестов имеют категорию `A`.

### Тестовые модули

| Модуль | MI |
| --- | ---: |
| `src/films/test_film_similar.py` | `26.33` |
| `src/persons/test_person_films.py` | `29.07` |
| `src/films/test_film_search.py` | `34.47` |
| `src/films/test_film_list.py` | `38.33` |
| `src/films/test_film_detail.py` | `41.10` |
| `src/genres/test_genre_list.py` | `45.42` |
| `src/persons/test_person_search.py` | `45.61` |
| `src/genres/test_genre_detail.py` | `46.58` |
| `src/persons/test_person_detail.py` | `46.84` |

### Тестовая инфраструктура

| Модуль | MI |
| --- | ---: |
| `testdata/films.py` | `43.29` |
| `utils/helpers.py` | `47.47` |
| `settings.py` | `48.01` |
| `utils/wait_for_es.py` | `60.89` |
| `utils/wait_for_redis.py` | `61.76` |
| `fixtures/films.py` | `63.22` |
| `testdata/persons.py` | `64.07` |
| `testdata/genres.py` | `66.90` |

`conftest.py`, общие fixture-модули, `responses.py` и package-файлы имеют MI `100.00`.

Низкие абсолютные значения отдельных `test_*` файлов объясняются количеством параметризованных сценариев и проверок. Файлы уже разделены по endpoint, поэтому дополнительное дробление не требуется.

## Проверка типов

Основной production-код полностью аннотирован. В функциональных тестах часть fixture и `test_*` функций пока не имеет аннотаций; рекомендуемые типы перечислены в итогах аудита.
