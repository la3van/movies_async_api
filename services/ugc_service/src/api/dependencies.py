"""Сборка зависимостей репозиториев и сервисного слоя."""

from typing import Annotated, Any

from cache.base import Cache
from cache.redis import RedisCache
from core.config import Settings, get_settings
from db.mongo import get_mongo
from db.redis import get_redis
from fastapi import Depends
from integrations.content import (
    ContentServiceClient,
    FilmCatalogService,
    get_content_client,
)
from redis.asyncio import Redis
from repositories.interfaces.bookmark import BookmarkRepository
from repositories.interfaces.rating import RatingRepository
from repositories.interfaces.reaction import ReviewReactionRepository
from repositories.interfaces.review import ReviewRepository
from repositories.mongo.bookmark import MongoBookmarkRepository
from repositories.mongo.rating import MongoRatingRepository
from repositories.mongo.reaction import MongoReviewReactionRepository
from repositories.mongo.review import MongoReviewRepository
from services.bookmark import BookmarkService
from services.rating import RatingService
from services.review import ReviewService


def get_cache(redis: Annotated[Redis, Depends(get_redis)]) -> Cache:
    return RedisCache(redis)


def get_film_catalog(
    client: Annotated[ContentServiceClient, Depends(get_content_client)],
    cache: Annotated[Cache, Depends(get_cache)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FilmCatalogService:
    return FilmCatalogService(
        client,
        cache,
        enabled=settings.content_validate_films,
    )


def get_bookmark_repository(
    database: Annotated[Any, Depends(get_mongo)],
) -> BookmarkRepository:
    return MongoBookmarkRepository(database)


def get_rating_repository(
    database: Annotated[Any, Depends(get_mongo)],
) -> RatingRepository:
    return MongoRatingRepository(database)


def get_review_repository(
    database: Annotated[Any, Depends(get_mongo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReviewRepository:
    return MongoReviewRepository(database, settings.review_sort_fields)


def get_reaction_repository(
    database: Annotated[Any, Depends(get_mongo)],
) -> ReviewReactionRepository:
    return MongoReviewReactionRepository(database)


def get_bookmark_service(
    repository: Annotated[
        BookmarkRepository, Depends(get_bookmark_repository)
    ],
    film_catalog: Annotated[FilmCatalogService, Depends(get_film_catalog)],
) -> BookmarkService:
    return BookmarkService(repository, film_catalog)


def get_rating_service(
    repository: Annotated[RatingRepository, Depends(get_rating_repository)],
    film_catalog: Annotated[FilmCatalogService, Depends(get_film_catalog)],
) -> RatingService:
    return RatingService(repository, film_catalog)


def get_review_service(
    reviews: Annotated[ReviewRepository, Depends(get_review_repository)],
    reactions: Annotated[
        ReviewReactionRepository,
        Depends(get_reaction_repository),
    ],
    film_catalog: Annotated[FilmCatalogService, Depends(get_film_catalog)],
) -> ReviewService:
    return ReviewService(reviews, reactions, film_catalog)
