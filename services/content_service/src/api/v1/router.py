"""Общий роутер API версии v1."""
from fastapi import APIRouter, Depends

from api.v1.endpoints import films, genres, persons
from auth.dependencies import require_permission


api_router = APIRouter(
    dependencies=[
        Depends(require_permission('content:read'))
    ],
)

api_router.include_router(
    router=films.router,
    prefix='/films',
    tags=['Кинопроизведения'],
)

api_router.include_router(
    router=genres.router,
    prefix='/genres',
    tags=['Жанры'],
)

api_router.include_router(
    router=persons.router,
    prefix='/persons',
    tags=['Персоны'],
)
