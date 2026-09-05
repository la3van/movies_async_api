"""Жизненный цикл подключения к MongoDB и создание индексов."""

from typing import Any

from core.config import get_settings
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel

mongo_client: AsyncMongoClient | None = None
mongo_database: Any | None = None


async def init_mongo() -> None:
    """Подключиться к MongoDB, проверить соединение и создать индексы."""
    global mongo_client, mongo_database
    settings = get_settings()

    mongo_client = AsyncMongoClient(
        settings.mongo_uri,
        connectTimeoutMS=settings.mongo_connect_timeout_ms,
        serverSelectionTimeoutMS=settings.mongo_server_selection_timeout_ms,
        socketTimeoutMS=settings.mongo_socket_timeout_ms,
        waitQueueTimeoutMS=settings.mongo_wait_queue_timeout_ms,
        timeoutMS=settings.mongo_operation_timeout_ms,
        maxPoolSize=settings.mongo_max_pool_size,
        minPoolSize=settings.mongo_min_pool_size,
        retryReads=True,
        retryWrites=True,
        tz_aware=True,
        uuidRepresentation="standard",
        appname=settings.project_name,
    )
    await mongo_client.admin.command("ping")
    mongo_database = mongo_client[settings.mongo_database]
    await _ensure_indexes(mongo_database)


async def _ensure_indexes(database: Any) -> None:
    """Создать уникальные и сортировочные индексы доменных коллекций."""
    await database.bookmarks.create_indexes(
        [
            IndexModel(
                [("user_id", ASCENDING), ("film_id", ASCENDING)],
                unique=True,
                name="uq_bookmark_user_film",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="ix_bookmark_user_created",
            ),
        ]
    )
    await database.ratings.create_indexes(
        [
            IndexModel(
                [("user_id", ASCENDING), ("film_id", ASCENDING)],
                unique=True,
                name="uq_rating_user_film",
            ),
            IndexModel(
                [("film_id", ASCENDING), ("value", ASCENDING)],
                name="ix_rating_film_value",
            ),
        ]
    )
    await database.reviews.create_indexes(
        [
            IndexModel(
                [("user_id", ASCENDING), ("film_id", ASCENDING)],
                unique=True,
                name="uq_review_user_film",
            ),
            IndexModel(
                [("film_id", ASCENDING), ("created_at", DESCENDING)],
                name="ix_review_film_created",
            ),
            IndexModel(
                [
                    ("film_id", ASCENDING),
                    ("created_at", DESCENDING),
                    ("_id", DESCENDING),
                ],
                name="ix_review_film_created_id",
            ),
            IndexModel(
                [
                    ("film_id", ASCENDING),
                    ("updated_at", DESCENDING),
                    ("_id", DESCENDING),
                ],
                name="ix_review_film_updated_id",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="ix_review_user_created",
            ),
        ]
    )
    await database.review_reactions.create_indexes(
        [
            IndexModel(
                [("user_id", ASCENDING), ("review_id", ASCENDING)],
                unique=True,
                name="uq_reaction_user_review",
            ),
            IndexModel(
                [("review_id", ASCENDING), ("value", ASCENDING)],
                name="ix_reaction_review_value",
            ),
        ]
    )


async def close_mongo() -> None:
    """Закрыть пул MongoDB."""
    global mongo_client, mongo_database
    if mongo_client is not None:
        await mongo_client.close()
    mongo_client = None
    mongo_database = None


async def get_mongo() -> Any:
    """Вернуть инициализированную базу данных."""
    if mongo_database is None:
        raise RuntimeError("MongoDB is not initialized")
    return mongo_database


async def mongo_is_ready() -> bool:
    """Проверить доступность MongoDB."""
    if mongo_client is None:
        return False
    try:
        await mongo_client.admin.command("ping")
    except Exception:
        return False
    return True
