# Централизованное логирование ELK

Общий Compose запускает следующую цепочку:

```text
stdout/stderr контейнеров
    → Filebeat
    → Logstash
    → Elasticsearch
    → Kibana
```

Filebeat использует Docker autodiscovery и читает логи всех контейнеров,
запущенных через Compose. В каждую запись добавляется `service.name` из
стандартной Compose-метки контейнера. Logstash сохраняет записи в индексы
вида `logs-<service>-YYYY.MM.dd`.

Nginx не требует отдельной настройки отправки логов: официальный образ пишет
access- и error-логи в stdout/stderr, откуда их забирает Filebeat.

## Запуск

Вместе со всей системой:

```bash
docker compose up -d --build
```

Только стек логирования и его зависимости:

```bash
docker compose up -d elasticsearch logstash filebeat kibana
```

Kibana доступна по адресу `http://127.0.0.1:5601`.

## Первоначальная настройка Kibana

После появления первых записей создайте data view:

1. откройте **Stack Management → Data Views**;
2. создайте data view с шаблоном `logs-*`;
3. выберите `@timestamp` как поле времени.

После этого записи доступны в **Discover**. Примеры фильтров:

```text
service.name: "nginx"
service.name: "auth-service" and message: "ERROR"
container.name: *ugc-service*
```

## Проверка

```bash
curl -fsS "http://127.0.0.1:5601/api/status"
curl -fsS "http://127.0.0.1:9200/_cat/indices/logs-*?v"
docker compose logs --tail=100 filebeat logstash kibana
```

Если индексов ещё нет, выполните несколько запросов к API через Nginx и
повторите проверку через несколько секунд.

## Хранение

Логи хранятся в том же Elasticsearch, что и поисковые индексы Content
Service, но в отдельных индексах `logs-*`. Для учебного окружения это
экономит память. В production поисковый и observability-кластеры следует
разделить, а для `logs-*` настроить ILM-политику удаления старых данных.

Позиции чтения Filebeat сохраняются в named volume `filebeat_data`, поэтому
после обычного перезапуска уже обработанные строки не отправляются повторно.

