# Infrastructure

Каталог содержит общие инфраструктурные артефакты проекта, которые не принадлежат одному конкретному приложению.

## Структура

```text
infrastructure/
├── elasticsearch/
│   ├── mappings/
│   │   ├── genres.json
│   │   ├── movies.json
│   │   └── persons.json
│   └── README.md
├── postgres/
│   ├── theatre/
│   │   └── init/
│   │       └── 0001_content_dump.sql
│   └── README.md
└── README.md
```

## Elasticsearch

[`elasticsearch/mappings`](elasticsearch/mappings) содержит settings и mappings индексов:

- `movies`;
- `genres`;
- `persons`.

Их используют:

- Content ETL при создании индексов;
- функциональные тесты Content Service.

Подробнее: [elasticsearch/README.md](elasticsearch/README.md).

## PostgreSQL

[`postgres/theatre/init`](postgres/theatre/init) содержит SQL-инициализацию исходной базы контента.

SQL-файлы монтируются в `/docker-entrypoint-initdb.d` контейнера `theatre-db` и выполняются официальным образом PostgreSQL при первом создании пустого volume.

Подробнее: [postgres/README.md](postgres/README.md).

## Правила изменений

- инфраструктурные файлы не должны импортироваться как Python-пакеты;
- mappings должны меняться синхронно с ETL и запросами Content Service;
- SQL init-скрипты выполняются только при создании новой PostgreSQL data directory;
- порядок SQL-скриптов задаётся числовым префиксом имени файла;
- секреты и локальные `.env` в этот каталог не добавляются.

## Повторная инициализация

Изменение init SQL не применяется к существующему PostgreSQL volume автоматически.

Полная очистка локального окружения:

```bash
docker compose down -v
docker compose up --build
```

Команда удаляет данные всех named volumes текущего Compose-проекта.
