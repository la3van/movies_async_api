# Content Service functional tests

Функциональные тесты проверяют Content Service через реальные HTTP-запросы в изолированном Docker Compose окружении.

## Что запускается

`functional/docker-compose.yml` поднимает:

| Сервис | Назначение |
| --- | --- |
| `content-service` | Тестируемое FastAPI-приложение под coverage.py |
| `elasticsearch` | Изолированный Elasticsearch с тестовыми индексами |
| `redis` | Изолированный Redis для API-кеша |
| `tests` | Контейнер с pytest |

PostgreSQL и Content ETL не нужны: тестовые документы загружаются в Elasticsearch напрямую через фикстуры.

## Структура

```text
tests/
├── functional/
│   ├── coverage/                      # .coverage и HTML-отчёт
│   ├── fixtures/
│   │   ├── common.py
│   │   ├── elastic.py
│   │   ├── films.py
│   │   ├── genres.py
│   │   ├── http.py
│   │   ├── persons.py
│   │   └── redis.py
│   ├── src/
│   │   ├── films/
│   │   │   ├── test_film_detail.py
│   │   │   ├── test_film_list.py
│   │   │   ├── test_film_search.py
│   │   │   └── test_film_similar.py
│   │   ├── genres/
│   │   │   ├── test_genre_detail.py
│   │   │   └── test_genre_list.py
│   │   └── persons/
│   │       ├── test_person_detail.py
│   │       ├── test_person_films.py
│   │       └── test_person_search.py
│   ├── test_data/
│   │   ├── films.py
│   │   ├── genres.py
│   │   ├── persons.py
│   │   └── responses.py
│   ├── utils/
│   │   ├── helpers.py
│   │   ├── wait_for_es.py
│   │   └── wait_for_redis.py
│   ├── conftest.py
│   ├── settings.py
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
└── README.md
```

## Организация фикстур

`conftest.py` регистрирует fixture-модули через `pytest_plugins`.

Фикстуры разделены на:

- инфраструктурные: event loop, HTTP, Elasticsearch и Redis;
- предметные: фильмы, жанры и персоны;
- вспомогательные: подготовка индексов, очистка кеша и ожидаемые ответы.

Тестовые файлы не импортируют fixtures напрямую: pytest разрешает зависимости по именам аргументов.

## Подготовка окружения

Из корня репозитория:

```bash
cd services/content_service/tests/functional
cp .env.example .env
```

В тестовом окружении `SERVICE_URL` должен указывать на Docker hostname:

```env
SERVICE_URL=http://content-service:8000
```

Mappings монтируются из:

```text
infrastructure/elasticsearch/mappings
```

в контейнер как:

```text
/app/mappings
```

## Запуск всех тестов

По умолчанию сервис и pytest-контейнер используют Python 3.10. Версию можно
переопределить, как в CI:

```bash
PYTHON_VERSION=3.12 docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```

Из каталога `services/content_service/tests/functional`:

```bash
docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```

Команда:

1. собирает образы;
2. поднимает Elasticsearch и Redis;
3. ждёт их healthcheck;
4. запускает Content Service;
5. ждёт готовности API;
6. запускает pytest;
7. возвращает exit-code контейнера `tests`.

## Прогресс тестов

Для подробного вывода с процентом выполнения используется:

```bash
pytest -vv -s -ra \
  --tb=short \
  --color=yes \
  -o console_output_style=progress-even-when-capture-no \
  tests/functional/src
```

Флаги:

- `-vv` — имя каждого теста;
- `-s` — живой stdout/stderr;
- `-ra` — summary дополнительных исходов;
- `--tb=short` — короткий traceback;
- `--color=yes` — цветной вывод;
- `console_output_style=progress-even-when-capture-no` — проценты даже при `-s`.

## Покрываемые сценарии

### Films

- получение фильма по UUID;
- список с пагинацией и сортировкой;
- фильтрация по жанру;
- полнотекстовый поиск;
- похожие фильмы;
- Redis cache hit;
- пустые результаты;
- `404` и ошибки валидации.

### Genres

- список жанров;
- поиск и сортировка;
- получение по UUID;
- кеширование;
- `404` и ошибки валидации.

### Persons

- поиск персон;
- получение персоны по UUID;
- фильмы персоны;
- сортировка и пагинация;
- кеширование;
- пустые результаты;
- `404` и ошибки валидации.

## Запуск отдельной группы или теста

Все тесты фильмов:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  -o console_output_style=progress-even-when-capture-no \
  tests/functional/src/films
```

Один файл:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/persons/test_person_search.py
```

Один тест:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/persons/test_person_search.py::test_person_search
```

## Coverage

Coverage собирается для `services/content_service/src`.

Текстовый отчёт:

```bash
docker compose run --rm --no-deps content-service coverage report -m
```

HTML-отчёт:

```bash
docker compose run --rm --no-deps content-service coverage html
```

Открыть HTML-отчёт на macOS:

```bash
open coverage/htmlcov/index.html
```

На момент текущего рефакторинга:

```text
TOTAL: 642 statements, 2 missed, 99% coverage
```

Непокрытые ветви относятся к обработке завершения/закрытия клиентов Elasticsearch и Redis.

## Остановка и очистка

```bash
docker compose down -v --remove-orphans
```

`-v` удаляет тестовые данные Elasticsearch и Redis. `--remove-orphans` полезен после переименования Compose services.

## Полезные команды

Посмотреть логи приложения:

```bash
docker compose logs content-service
```

Проверить итоговую Compose-конфигурацию:

```bash
docker compose config
```

Пересобрать после изменения кода:

```bash
docker compose up --build --force-recreate \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```
