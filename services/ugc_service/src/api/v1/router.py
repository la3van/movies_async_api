"""Общий роутер API версии v1."""

from api.v1.endpoints import bookmarks, ratings, reviews
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(
    bookmarks.router,
    prefix="/bookmarks",
    tags=["Закладки"],
)
api_router.include_router(
    ratings.router,
    prefix="/ratings",
    tags=["Оценки"],
)
api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["Рецензии"],
)
