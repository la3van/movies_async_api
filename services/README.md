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
| `notification_service` | FastAPI и фоновые процессы | PostgreSQL и Kafka | [документация](notification_service/README.md) |
| `notification_worker` | Consumer и SMTP-отправитель | PostgreSQL, Kafka и SMTP | [документация](notification_worker/README.md) |
| `ugc_service` | FastAPI | MongoDB и Redis | [документация](ugc_service/README.md) |

## Связи

- `admin-service` делегирует проверку учётных данных `auth-service`;
- `content-service` использует Auth Service для проверки permissions;
- `events-service` принимает только события авторизованных пользователей;
- `ugc-service` проверяет пользователя через Auth Service, а существование
  фильма — через Content Service;
- `content-etl` формирует поисковую read model для Content Service;
- `events-etl` переносит поток из Kafka в ClickHouse;
- `notification-service` принимает заявки и события, создаёт задания в Kafka;
- `notification-worker` получает данные адресата из Auth, отправляет письма
  и возвращает результаты через Kafka.

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

## Наблюдаемость

Логи всех Compose-контейнеров собираются Filebeat, проходят через Logstash и
сохраняются в Elasticsearch в индексах `logs-*`. Просмотр выполняется в
Kibana на `http://127.0.0.1:5601`.

Каждый Python-компонент подключает Sentry SDK, но отправка отключена, пока в
его `.env` не указан `SENTRY_DSN`. HTTP-сервисы используют интеграции своего
фреймворка, а ETL отправляют необработанные исключения и ERROR-логи.

Инструкции: [ELK](../infrastructure/elk/README.md) и
[Sentry](../infrastructure/sentry/README.md).

## Проверки

Ruff проверяет весь монорепозиторий. Mypy и компиляция выполняются отдельно
для каждого сервиса на Python 3.10, 3.11 и 3.12. Функциональные pytest-наборы
Auth и Content Services запускаются в CI в изолированных Compose-проектах.
Для двух сервисов уведомлений автоматические тесты не добавлены.
[Ручная проверка обоих приложений](notification_service/README.md#ручная-проверка-обоих-сервисов).