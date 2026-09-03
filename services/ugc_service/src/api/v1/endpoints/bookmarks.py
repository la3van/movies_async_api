"""CRUD пользовательских закладок."""

from typing import Annotated
from uuid import UUID

from api.dependencies import get_bookmark_service
from api.v1.mappers.bookmarks import build_bookmark_response
from api.v1.schemas.bookmarks import BookmarkResponse
from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser
from core.rate_limit import rate_limit
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from services.bookmark import BookmarkService

router = APIRouter()


@router.get(
    "/",
    response_model=list[BookmarkResponse],
    summary="Список закладок текущего пользователя",
)
async def list_bookmarks(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
    page_number: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> list[BookmarkResponse]:
    bookmarks = await service.list(current_user.id, page_number, page_size)
    return [build_bookmark_response(item) for item in bookmarks]


@router.get(
    "/{film_id}",
    response_model=BookmarkResponse,
    summary="Проверка наличия фильма в закладках",
)
async def get_bookmark(
    film_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkResponse:
    bookmark = await service.get(current_user.id, film_id)
    if bookmark is None:
        raise HTTPException(status_code=404, detail="bookmark_not_found")
    return build_bookmark_response(bookmark)


@router.put(
    "/{film_id}",
    response_model=BookmarkResponse,
    dependencies=[
        Depends(
            rate_limit(scope="bookmarks:write", requests=60, window_seconds=60)
        )
    ],
    summary="Добавление фильма в закладки",
)
async def add_bookmark(
    film_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkResponse:
    bookmark = await service.add(
        user=current_user,
        film_id=film_id,
        request_id=request.state.request_id,
    )
    return build_bookmark_response(bookmark)


@router.delete(
    "/{film_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            rate_limit(scope="bookmarks:write", requests=60, window_seconds=60)
        )
    ],
    summary="Удаление фильма из закладок",
)
async def delete_bookmark(
    film_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> None:
    await service.delete(current_user.id, film_id)
