"""Бизнес-логика пользовательских закладок."""

from uuid import UUID

from auth.models import AuthenticatedUser
from core.tracing import trace_method
from integrations.content import FilmCatalogService
from models.bookmark import Bookmark
from repositories.interfaces.bookmark import BookmarkRepository


class BookmarkService:
    """Управлять персональным списком отложенных фильмов."""

    def __init__(
        self,
        repository: BookmarkRepository,
        film_catalog: FilmCatalogService,
    ) -> None:
        self._repository = repository
        self._film_catalog = film_catalog

    @trace_method("ugc.bookmarks.add")
    async def add(
        self,
        *,
        user: AuthenticatedUser,
        film_id: UUID,
        request_id: str,
    ) -> Bookmark:
        await self._film_catalog.ensure_exists(
            film_id,
            access_token=user.access_token,
            request_id=request_id,
        )
        return await self._repository.upsert(user.id, film_id)

    @trace_method("ugc.bookmarks.get")
    async def get(self, user_id: UUID, film_id: UUID) -> Bookmark | None:
        return await self._repository.get(user_id, film_id)

    @trace_method("ugc.bookmarks.list")
    async def list(
        self, user_id: UUID, page_number: int, page_size: int
    ) -> list[Bookmark]:
        return await self._repository.list_by_user(
            user_id, page_number, page_size
        )

    @trace_method("ugc.bookmarks.delete")
    async def delete(self, user_id: UUID, film_id: UUID) -> None:
        await self._repository.delete(user_id, film_id)
