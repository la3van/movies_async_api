"""MongoDB-репозиторий пользовательских закладок."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.exceptions import DependencyUnavailableError
from models.bookmark import Bookmark
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from repositories.interfaces.bookmark import BookmarkRepository
from repositories.mongo.mappers import build_bookmark


class MongoBookmarkRepository(BookmarkRepository):
    """Хранить уникальные пары user_id/film_id в MongoDB."""

    def __init__(self, database: Any) -> None:
        self._collection = database.bookmarks

    async def upsert(self, user_id: UUID, film_id: UUID) -> Bookmark:
        now = datetime.now(timezone.utc)
        try:
            document = await self._collection.find_one_and_update(
                {"user_id": str(user_id), "film_id": str(film_id)},
                {"$setOnInsert": {"created_at": now}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            try:
                document = await self._collection.find_one(
                    {"user_id": str(user_id), "film_id": str(film_id)}
                )
            except PyMongoError as error:
                raise DependencyUnavailableError(
                    "MongoDB unavailable"
                ) from error
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        if document is None:
            raise DependencyUnavailableError("MongoDB did not return bookmark")
        return build_bookmark(document)

    async def get(self, user_id: UUID, film_id: UUID) -> Bookmark | None:
        try:
            document = await self._collection.find_one(
                {"user_id": str(user_id), "film_id": str(film_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return build_bookmark(document) if document else None

    async def list_by_user(
        self, user_id: UUID, page_number: int, page_size: int
    ) -> list[Bookmark]:
        try:
            cursor = (
                self._collection.find({"user_id": str(user_id)})
                .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
                .skip((page_number - 1) * page_size)
                .limit(page_size)
            )
            documents = await cursor.to_list(length=page_size)
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return [build_bookmark(document) for document in documents]

    async def delete(self, user_id: UUID, film_id: UUID) -> bool:
        try:
            result = await self._collection.delete_one(
                {"user_id": str(user_id), "film_id": str(film_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return result.deleted_count == 1
