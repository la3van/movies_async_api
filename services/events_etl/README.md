# Events ETL

Фоновый процесс переноса пользовательских событий из Kafka в ClickHouse.

## Поток данных

```text
Kafka user-events
    → batch consumer
    → валидация и преобразование
    → ClickHouse analytics.user_events
```

Некорректные события публикуются в topic `user-events-dlq`. Kafka offsets
подтверждаются только после записи валидных событий в ClickHouse и успешной
отправки отклонённых сообщений в DLQ.

## Возможности

- пакетное чтение Kafka;
- ручное подтверждение offsets;
- повторные попытки подключения и записи;
- безопасный replay благодаря дедупликации по `event_id`;
- корректное завершение по `SIGTERM` и `SIGINT`;
- Prometheus-метрики на порту `9100`;
- отдельный Dead Letter Queue для невалидных сообщений.

## Зависимости

- Kafka topics `user-events` и `user-events-dlq`;
- ClickHouse database `analytics` и таблица `user_events`.

Topics создаёт контейнер `kafka-init`, а таблицу — файл
`infrastructure/clickhouse/init.sql`.

## Конфигурация и запуск

```bash
cp services/events_etl/.env.example services/events_etl/.env
docker compose up -d --build events-etl
```

Метрики доступны по адресу `http://127.0.0.1:9100/metrics`. Все параметры
Kafka, ClickHouse, retry, batch processing и DLQ перечислены в
`.env.example`.

## Проверки

Отдельного набора pytest у процесса пока нет. CI выполняет Ruff, mypy,
установку зависимостей и компиляцию исходников на Python 3.10, 3.11 и 3.12.
