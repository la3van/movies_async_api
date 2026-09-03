"""MongoDB-репозиторий пользовательских оценок."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.exceptions import DependencyUnavailableError
from models.rating import FilmRatingStats, Rating, RatingDistributionItem
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from repositories.interfaces.rating import RatingRepository
from repositories.mongo.mappers import build_rating
from repositories.mongo.pipelines.ratings import build_rating_stats_pipeline


class MongoRatingRepository(RatingRepository):
    """Хранить одну оценку пользователя на фильм и считать агрегаты."""

    def __init__(self, database: Any) -> None:
        self._collection = database.ratings

    async def upsert(self, user_id: UUID, film_id: UUID, value: int) -> Rating:
        now = datetime.now(timezone.utc)
        try:
            document = await self._collection.find_one_and_update(
                {"user_id": str(user_id), "film_id": str(film_id)},
                {
                    "$set": {"value": value, "updated_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            try:
                document = await self._collection.find_one_and_update(
                    {"user_id": str(user_id), "film_id": str(film_id)},
                    {"$set": {"value": value, "updated_at": now}},
                    return_document=ReturnDocument.AFTER,
                )
            except PyMongoError as error:
                raise DependencyUnavailableError(
                    "MongoDB unavailable"
                ) from error
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        if document is None:
            raise DependencyUnavailableError("MongoDB did not return rating")
        return build_rating(document)

    async def get(self, user_id: UUID, film_id: UUID) -> Rating | None:
        try:
            document = await self._collection.find_one(
                {"user_id": str(user_id), "film_id": str(film_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return build_rating(document) if document else None

    async def delete(self, user_id: UUID, film_id: UUID) -> bool:
        try:
            result = await self._collection.delete_one(
                {"user_id": str(user_id), "film_id": str(film_id)}
            )
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error
        return result.deleted_count == 1

    async def get_film_stats(self, film_id: UUID) -> FilmRatingStats:
        try:
            cursor = self._collection.aggregate(
                build_rating_stats_pipeline(str(film_id))
            )
            documents = await cursor.to_list(length=1)
        except PyMongoError as error:
            raise DependencyUnavailableError("MongoDB unavailable") from error

        raw = documents[0] if documents else {}
        counts = {
            int(item["value"]): int(item["count"])
            for item in raw.get("distribution", [])
        }
        return FilmRatingStats(
            film_id=film_id,
            rating_count=raw.get("rating_count", 0),
            average_rating=raw.get("average_rating"),
            likes_count=raw.get("likes_count", 0),
            dislikes_count=raw.get("dislikes_count", 0),
            distribution=[
                RatingDistributionItem(value=value, count=counts.get(value, 0))
                for value in range(11)
            ],
        )
