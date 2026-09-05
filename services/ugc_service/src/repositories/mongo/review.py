"""MongoDB-репозиторий рецензий."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.exceptions import (
    DependencyUnavailableError,
    ResourceConflictError,
    ReviewNotFoundError,
)
from core.pagination import ReviewCursor
from models.review import Review, ReviewDetails
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from repositories.interfaces.review import ReviewRepository
from repositories.mongo.mappers import build_review, build_review_details
from repositories.mongo.pipelines.reviews import (
    build_review_details_stages,
    build_review_list_pipeline,
)


class MongoReviewRepository(ReviewRepository):
    """Хранить рецензии и присоединять оценки/голоса через aggregation."""

    def __init__(self, database: Any, sort_fields: dict[str, str]) -> None:
        self._database = database
        self._collection = database.reviews
        self._reactions = database.review_reactions
        self._sort_fields = sort_fields

    async def create(self, review: Review) -> Review:
        document = {
            "_id": str(review.id),
            "film_id": str(review.film_id),
            "user_id": str(review.user_id),
            "author_login": review.author_login,
            "text": review.text,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        }
        try:
            await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            raise ResourceConflictError(
                "User already has a review for this film"
            ) from error
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return review

    async def get(self, review_id: UUID) -> Review | None:
        try:
            document = await self._collection.find_one({"_id": str(review_id)})
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return build_review(document) if document else None

    async def get_details(self, review_id: UUID) -> ReviewDetails | None:
        pipeline = [
            {"$match": {"_id": str(review_id)}},
            *build_review_details_stages(),
            {"$limit": 1},
        ]
        try:
            cursor = self._collection.aggregate(pipeline)
            documents = await cursor.to_list(length=1)
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return build_review_details(documents[0]) if documents else None

    async def list_by_film(
        self,
        film_id: UUID,
        sort: str,
        cursor: ReviewCursor | None,
        page_size: int,
    ) -> list[ReviewDetails]:
        pipeline = build_review_list_pipeline(
            film_id=str(film_id),
            sort=sort,
            sort_fields=self._sort_fields,
            cursor=cursor,
            page_size=page_size,
        )
        try:
            mongo_cursor = self._collection.aggregate(pipeline)
            documents = await mongo_cursor.to_list(length=page_size)
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error

        return [build_review_details(document) for document in documents]

    async def update_text(self, review_id: UUID, text: str) -> Review:
        try:
            document = await self._collection.find_one_and_update(
                {"_id": str(review_id)},
                {
                    "$set": {
                        "text": text,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        if document is None:
            raise ReviewNotFoundError
        return build_review(document)

    async def delete_with_reactions(self, review_id: UUID) -> bool:
        """Удалить рецензию и реакции в одной MongoDB-транзакции."""

        async def delete_in_transaction(session: Any) -> bool:
            await self._reactions.delete_many(
                {"review_id": str(review_id)},
                session=session,
            )
            result = await self._collection.delete_one(
                {"_id": str(review_id)},
                session=session,
            )
            return result.deleted_count == 1

        try:
            async with self._database.client.start_session() as session:
                return await session.with_transaction(
                    delete_in_transaction,
                    max_commit_time_ms=5_000,
                )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
