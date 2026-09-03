# Services

Все прикладные компоненты проекта изолированы по каталогам и имеют собственные
Dockerfile, зависимости, конфигурацию и README.

## Состав

| Каталог | Тип | Хранилище или транспорт | README |
| --- | --- | --- | --- |
| `admin_service` | Django Admin | PostgreSQL и SQLite | [документация](admin_service/README.md) |
| `auth_service` | FastAPI | PostgreSQL и Redis | [документация](auth_service/README.md) |
| `content_service` | FastAPI | Elasticsearch и Redis | [документация](content_service/README.md) |
| `content_etl` | фоновый ETL | PostgreSQL, Elasticsearch и Redis | [документация](content_etl/README.md) |
| `events_service` | Flask API | Kafka и Redis | [документация](events_service/README.md) |
| `events_etl` | фоновый ETL | Kafka и ClickHouse | [документация](events_etl/README.md) |
| `ugc_service` | FastAPI | MongoDB и Redis | [документация](ugc_service/README.md) |

## Связи

- `admin-service` делегирует проверку учётных данных `auth-service`;
- `content-service` использует Auth Service для проверки permissions;
- `events-service` принимает только события авторизованных пользователей;
- `ugc-service` проверяет пользователя через Auth Service, а существование
  фильма — через Content Service;
- `content-etl` формирует поисковую read model для Content Service;
- `events-etl` переносит поток из Kafka в ClickHouse.

Redis разделён логическими DB:

| DB | Потребитель |
| --- | --- |
| `0` | Content ETL state |
| `1` | Content Service cache |
| `2` | Auth Service cache |
| `3` | Events Service rate limiting |
| `4` | UGC Service rate limiting и служебный кеш |

## Запуск

Сервисы рассчитаны на запуск из корневого `docker-compose.yml`:

```bash
docker compose up -d --build
```

Запуск одного компонента вместе с его зависимостями:

```bash
docker compose up -d --build ugc-service
```

Переменные окружения документированы в `.env.example` каждого сервиса.

## Проверки

Ruff проверяет весь монорепозиторий. Mypy и компиляция выполняются отдельно
для каждого сервиса на Python 3.10, 3.11 и 3.12. Функциональные pytest-наборы
Auth и Content Services запускаются в CI в изолированных Compose-проектах.