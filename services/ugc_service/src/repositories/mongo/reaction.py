"""MongoDB-репозиторий голосов за рецензии."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.exceptions import DependencyUnavailableError
from models.reaction import ReactionValue, ReviewReaction
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from repositories.interfaces.reaction import ReviewReactionRepository
from repositories.mongo.mappers import build_reaction


class MongoReviewReactionRepository(ReviewReactionRepository):
    """Хранить один голос пользователя на рецензию."""

    def __init__(self, database: Any) -> None:
        self._collection = database.review_reactions

    async def upsert(
        self,
        user_id: UUID,
        review_id: UUID,
        value: ReactionValue,
    ) -> ReviewReaction:
        now = datetime.now(timezone.utc)
        try:
            document = await self._collection.find_one_and_update(
                {"user_id": str(user_id), "review_id": str(review_id)},
                {
                    "$set": {"value": int(value), "updated_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            try:
                document = await self._collection.find_one_and_update(
                    {"user_id": str(user_id), "review_id": str(review_id)},
                    {"$set": {"value": int(value), "updated_at": now}},
                    return_document=ReturnDocument.AFTER,
                )
            except PyMongoError as error:
                raise DependencyUnavailableError(
                    "MongoDB unavailable"
                ) from error
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        if document is None:
            raise DependencyUnavailableError("MongoDB did not return reaction")
        return build_reaction(document)

    async def get(
        self, user_id: UUID, review_id: UUID
    ) -> ReviewReaction | None:
        try:
            document = await self._collection.find_one(
                {"user_id": str(user_id), "review_id": str(review_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return build_reaction(document) if document else None

    async def delete(self, user_id: UUID, review_id: UUID) -> bool:
        try:
            result = await self._collection.delete_one(
                {"user_id": str(user_id), "review_id": str(review_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return result.deleted_count == 1

    async def delete_for_review(self, review_id: UUID) -> None:
        try:
            await self._collection.delete_many({"review_id": str(review_id)})
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
