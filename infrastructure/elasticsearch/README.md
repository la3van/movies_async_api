# Elasticsearch infrastructure

Каталог содержит settings и mappings Elasticsearch-индексов контентного домена.

## Структура

```text
elasticsearch/
├── mappings/
│   ├── genres.json
│   ├── movies.json
│   └── persons.json
└── README.md
```

| Файл | Индекс | Назначение |
| --- | --- | --- |
| `mappings/movies.json` | `movies` | Фильмы, жанры, участники и поля поиска |
| `mappings/genres.json` | `genres` | Жанры |
| `mappings/persons.json` | `persons` | Персоны, роли и связанные фильмы |

## Использование

Mappings используют два компонента:

1. Content ETL — создаёт недостающие индексы до запуска pipelines;
2. функциональные тесты Content Service — создают изолированные тестовые индексы.

В контейнеры каталог монтируется как:

```text
/app/mappings
```

Путь передаётся через:

```env
SCHEMAS_DIR=/app/mappings
```

Имя переменной сохранено для совместимости существующей конфигурации.

## Изменение mapping

При добавлении или изменении поля проверьте:

- модель документа в Content ETL;
- transform соответствующего pipeline;
- Elasticsearch query bodies в Content Service;
- разрешённые sort fields;
- тестовые документы и ожидаемые ответы;
- функциональные тесты.

Elasticsearch не позволяет произвольно менять тип существующего поля. Для несовместимых изменений обычно требуется новый индекс и переиндексация.

## Проверка индексов

```bash
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/movies/_mapping?pretty"
curl "http://localhost:9200/genres/_mapping?pretty"
curl "http://localhost:9200/persons/_mapping?pretty"
```

## Пересоздание локальных индексов

```bash
docker compose down -v
docker compose up --build
```

Команда удалит также PostgreSQL и Redis volumes корневого Compose-проекта.
