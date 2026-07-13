# PostgreSQL infrastructure

Каталог содержит SQL-файлы инициализации PostgreSQL-баз, которые создаются через `/docker-entrypoint-initdb.d`.

## Структура

```text
postgres/
├── theatre/
│   └── init/
│       └── 0001_content_dump.sql
└── README.md
```

## Theatre database

`theatre` — исходная база фильмов, жанров и персон для Content ETL.

Файл:

```text
theatre/init/0001_content_dump.sql
```

содержит структуру и начальные данные контентной базы.

В корневом `docker-compose.yml` каталог монтируется так:

```yaml
volumes:
  - ./infrastructure/postgres/theatre/init:/docker-entrypoint-initdb.d:ro
```

Важно монтировать каталог в каталог. Монтирование каталога `init` в путь файла вроде `/docker-entrypoint-initdb.d/init.sql` приведёт к ошибке `Is a directory`.

## Порядок выполнения

Официальный образ PostgreSQL выполняет поддерживаемые init-файлы в алфавитном порядке.

Числовые префиксы позволяют управлять очередностью:

```text
0001_content_dump.sql
0002_additional_seed.sql
0003_indexes.sql
```

## Когда выполняются init-скрипты

Скрипты запускаются только при инициализации пустой PostgreSQL data directory.

Если volume уже существует, изменение SQL-файла само по себе не изменит базу.

## Повторная инициализация

Удалить все volumes корневого Compose-проекта:

```bash
docker compose down -v
docker compose up --build
```

Удалить только volume контентной PostgreSQL-базы:

```bash
docker compose down
docker volume ls
docker volume rm <project>_postgres_data
docker compose up --build
```

Точное имя volume зависит от Compose project name.

## Проверка базы

```bash
docker compose exec theatre-db \
  psql -U postgres -d theatre
```

Показать схемы:

```bash
docker compose exec theatre-db \
  psql -U postgres -d theatre -c "\\dn"
```

Показать таблицы схемы `content`:

```bash
docker compose exec theatre-db \
  psql -U postgres -d theatre -c "\\dt content.*"
```

## Auth PostgreSQL

Auth Service не использует SQL init-дамп из этого каталога. Его структура управляется Alembic-миграциями из `services/auth_service/alembic`.
