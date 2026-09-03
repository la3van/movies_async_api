"""CRUD рецензий и лайков/дизлайков рецензий."""

from typing import Annotated
from uuid import UUID

from api.dependencies import get_review_service
from api.v1.mappers.reviews import (
    build_reaction_response,
    build_review_response,
)
from api.v1.schemas.reviews import (
    ReactionResponse,
    ReactionUpsertRequest,
    ReviewCreateRequest,
    ReviewResponse,
    ReviewUpdateRequest,
)
from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser
from core.rate_limit import rate_limit
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from models.reaction import ReactionValue
from services.review import ReviewService

router = APIRouter()


@router.get(
    "/films/{film_id}",
    response_model=list[ReviewResponse],
    summary="Список рецензий фильма с гибкой сортировкой",
)
async def list_reviews(
    film_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
    sort: str = Query(
        "-published_at",
        pattern=r"^-?(published_at|updated_at|likes|dislikes|helpfulness|author_rating)$",
        description="Поле сортировки; '-' означает порядок по убыванию",
    ),
    page_number: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> list[ReviewResponse]:
    reviews = await service.list_by_film(
        user=current_user,
        film_id=film_id,
        sort=sort,
        page_number=page_number,
        page_size=page_size,
        request_id=request.state.request_id,
    )
    return [build_review_response(review) for review in reviews]


@router.post(
    "/films/{film_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(scope="reviews:create", requests=10, window_seconds=60)
        )
    ],
    summary="Публикация рецензии на фильм",
)
async def create_review(
    film_id: UUID,
    payload: ReviewCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    review = await service.create(
        user=current_user,
        film_id=film_id,
        text=payload.text,
        request_id=request.state.request_id,
    )
    return build_review_response(review)


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Получение одной рецензии",
)
async def get_review(
    review_id: UUID,
    _current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    return build_review_response(await service.get(review_id))


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    dependencies=[
        Depends(
            rate_limit(scope="reviews:update", requests=30, window_seconds=60)
        )
    ],
    summary="Изменение своей рецензии",
)
async def update_review(
    review_id: UUID,
    payload: ReviewUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    review = await service.update(
        review_id=review_id,
        user_id=current_user.id,
        text=payload.text,
    )
    return build_review_response(review)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            rate_limit(scope="reviews:delete", requests=30, window_seconds=60)
        )
    ],
    summary="Удаление своей рецензии",
)
async def delete_review(
    review_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> None:
    await service.delete(review_id=review_id, user_id=current_user.id)


@router.get(
    "/{review_id}/reaction",
    response_model=ReactionResponse,
    summary="Голос текущего пользователя за рецензию",
)
async def get_reaction(
    review_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReactionResponse:
    reaction = await service.get_reaction(
        review_id=review_id,
        user_id=current_user.id,
    )
    if reaction is None:
        raise HTTPException(status_code=404, detail="reaction_not_found")
    return build_reaction_response(reaction)


@router.put(
    "/{review_id}/reaction",
    response_model=ReactionResponse,
    dependencies=[
        Depends(
            rate_limit(scope="reactions:write", requests=60, window_seconds=60)
        )
    ],
    summary="Лайк или дизлайк рецензии",
)
async def upsert_reaction(
    review_id: UUID,
    payload: ReactionUpsertRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReactionResponse:
    value = (
        ReactionValue.LIKE
        if payload.value == "like"
        else ReactionValue.DISLIKE
    )
    reaction = await service.upsert_reaction(
        review_id=review_id,
        user_id=current_user.id,
        value=value,
    )
    return build_reaction_response(reaction)


@router.delete(
    "/{review_id}/reaction",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            rate_limit(scope="reactions:write", requests=60, window_seconds=60)
        )
    ],
    summary="Удаление своего голоса за рецензию",
)
async def delete_reaction(
    review_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> None:
    await service.delete_reaction(
        review_id=review_id,
        user_id=current_user.id,
    )
