"""MongoDB-репозиторий голосов за рецензии."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.exceptions import (
    DependencyUnavailableError,
    ReviewNotFoundError,
)
from models.reaction import ReactionValue, ReviewReaction
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from repositories.interfaces.reaction import ReviewReactionRepository
from repositories.mongo.mappers import build_reaction


class MongoReviewReactionRepository(ReviewReactionRepository):
    """Хранить один голос пользователя на рецензию."""

    def __init__(self, database: Any) -> None:
        self._database = database
        self._collection = database.review_reactions
        self._reviews = database.reviews

    async def upsert(
        self,
        user_id: UUID,
        review_id: UUID,
        value: ReactionValue,
    ) -> ReviewReaction:
        now = datetime.now(timezone.utc)

        async def upsert_in_transaction(session: Any) -> ReviewReaction:
            review_result = await self._reviews.update_one(
                {"_id": str(review_id)},
                {"$inc": {"reaction_version": 1}},
                session=session,
            )
            if review_result.matched_count == 0:
                raise ReviewNotFoundError

            document = await self._collection.find_one_and_update(
                {
                    "user_id": str(user_id),
                    "review_id": str(review_id),
                },
                {
                    "$set": {
                        "value": int(value),
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "created_at": now,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            if document is None:
                raise DependencyUnavailableError(
                    "MongoDB did not return reaction"
                )

            return build_reaction(document)

        try:
            async with self._database.client.start_session() as session:
                return await session.with_transaction(
                    upsert_in_transaction,
                    max_commit_time_ms=5_000,
                )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error

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
