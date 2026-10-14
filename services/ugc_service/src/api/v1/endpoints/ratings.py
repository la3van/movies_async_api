"""CRUD оценок и агрегированная статистика фильма."""

from typing import Annotated
from uuid import UUID

from api.dependencies import get_rating_service
from api.v1.mappers.ratings import (
    build_rating_response,
    build_rating_stats_response,
)
from api.v1.schemas.ratings import (
    FilmRatingStatsResponse,
    RatingResponse,
    RatingUpsertRequest,
    UserRatingPageResponse,
)
from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser
from core.rate_limit import rate_limit
from fastapi import APIRouter, Depends, Query, Request, status
from services.rating import RatingService

router = APIRouter()


@router.get(
    "/me",
    response_model=UserRatingPageResponse,
    summary="Все оценки текущего пользователя",
)
async def list_my_ratings(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RatingService, Depends(get_rating_service)],
    after: UUID | None = None,
    page_size: int = Query(50, ge=1, le=100),
) -> UserRatingPageResponse:
    ratings = await service.list_by_user(current_user.id, after, page_size + 1)
    items = [build_rating_response(item) for item in ratings[:page_size]]
    return UserRatingPageResponse(
        items=items,
        next_cursor=(items[-1].film_id if len(ratings) > page_size else None),
    )


@router.get(
    "/{film_id}/stats",
    response_model=FilmRatingStatsResponse,
    summary="Пользовательский рейтинг фильма",
)
async def get_rating_stats(
    film_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RatingService, Depends(get_rating_service)],
) -> FilmRatingStatsResponse:
    stats = await service.get_stats(
        user=current_user,
        film_id=film_id,
        request_id=request.state.request_id,
    )
    return build_rating_stats_response(stats)


@router.get(
    "/{film_id}",
    response_model=RatingResponse,
    summary="Оценка текущего пользователя",
)
async def get_rating(
    film_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RatingService, Depends(get_rating_service)],
) -> RatingResponse:
    rating = await service.get_current(current_user.id, film_id)
    return build_rating_response(rating)


@router.put(
    "/{film_id}",
    response_model=RatingResponse,
    dependencies=[
        Depends(
            rate_limit(scope="ratings:write", requests=60, window_seconds=60)
        )
    ],
    summary="Добавление или изменение оценки фильма",
)
async def upsert_rating(
    film_id: UUID,
    payload: RatingUpsertRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RatingService, Depends(get_rating_service)],
) -> RatingResponse:
    rating = await service.upsert(
        user=current_user,
        film_id=film_id,
        value=payload.value,
        request_id=request.state.request_id,
    )
    return build_rating_response(rating)


@router.delete(
    "/{film_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            rate_limit(scope="ratings:write", requests=60, window_seconds=60)
        )
    ],
    summary="Удаление оценки фильма",
)
async def delete_rating(
    film_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RatingService, Depends(get_rating_service)],
) -> None:
    await service.delete(current_user.id, film_id)
