# Events Service

Flask API для приёма пользовательских событий онлайн-кинотеатра и их
надёжной публикации в Kafka.

## Назначение

Сервис принимает события `click`, `page_view`, `video_started`,
`video_progress`, `video_finished`, `video_quality_changed` и
`search_filter_used`. Пользователь определяется по access token через
`auth-service`; переданный клиентом `user_id` не считается доверенным.

После валидации Pydantic событие дополняется временем приёма и
`X-Request-ID`, а затем отправляется в Kafka topic `user-events`.

## Зависимости

- `auth-service` — проверка пользователя;
- Redis DB 3 — rate limiting;
- Kafka — хранение потока событий;
- Jaeger — распределённая трассировка.

Producer использует `acks=all`, idempotence и ожидание подтверждения
доставки. При недоступности Kafka API возвращает `503`, а не сообщает об
успешном приёме события.

## API

| Метод | URL | Назначение |
| --- | --- | --- |
| `POST` | `/api/v1/events` | принять пользовательское событие |
| `GET` | `/health` | проверить процесс |
| `GET` | `/ready` | проверить внешние зависимости |

Успешный запрос возвращает `202 Accepted` и `event_id`. Для доменного endpoint
обязателен заголовок `Authorization: Bearer <access-token>`.

## Конфигурация и запуск

```bash
cp services/events_service/.env.example services/events_service/.env
docker compose up -d --build events-service
```

В общем окружении endpoint доступен через Nginx:

```text
POST http://127.0.0.1:8000/api/v1/events
```

Основные настройки Kafka, Auth Service, Redis, Gunicorn и OpenTelemetry
описаны в `.env.example`.

## Проверки

Отдельного набора pytest у сервиса пока нет. CI выполняет Ruff, mypy,
установку зависимостей и компиляцию исходников на Python 3.10, 3.11 и 3.12.

## Логи и Sentry

Логи контейнера автоматически поступают в общий ELK-стек и доступны в
Kibana по фильтру `service.name: "events-service"`. Flask-ошибки отправляются
в Sentry, если в `.env` задан `SENTRY_DSN`; пустое значение отключает SDK.

Подробности: [Sentry](../../infrastructure/sentry/README.md) и
[ELK](../../infrastructure/elk/README.md).