"""Бизнес-логика оценок фильмов."""

from uuid import UUID

from auth.models import AuthenticatedUser
from core.exceptions import RatingNotFoundError
from core.tracing import trace_method
from integrations.content import FilmCatalogService
from models.rating import FilmRatingStats, Rating
from repositories.interfaces.rating import RatingRepository


class RatingService:
    """Управлять оценкой пользователя и агрегатами фильма."""

    async def list_by_user(
        self, user_id: UUID, after: UUID | None, limit: int
    ) -> list[Rating]:
        return await self._repository.list_by_user(user_id, after, limit)

    def __init__(
        self,
        repository: RatingRepository,
        film_catalog: FilmCatalogService,
    ) -> None:
        self._repository = repository
        self._film_catalog = film_catalog

    @trace_method("ugc.ratings.upsert")
    async def upsert(
        self,
        *,
        user: AuthenticatedUser,
        film_id: UUID,
        value: int,
        request_id: str,
    ) -> Rating:
        await self._film_catalog.ensure_exists(
            film_id,
            access_token=user.access_token,
            request_id=request_id,
        )
        return await self._repository.upsert(user.id, film_id, value)

    @trace_method("ugc.ratings.get_current")
    async def get_current(self, user_id: UUID, film_id: UUID) -> Rating:
        rating = await self._repository.get(user_id, film_id)
        if rating is None:
            raise RatingNotFoundError
        return rating

    @trace_method("ugc.ratings.delete")
    async def delete(self, user_id: UUID, film_id: UUID) -> None:
        await self._repository.delete(user_id, film_id)

    @trace_method("ugc.ratings.stats")
    async def get_stats(
        self,
        *,
        user: AuthenticatedUser,
        film_id: UUID,
        request_id: str,
    ) -> FilmRatingStats:
        await self._film_catalog.ensure_exists(
            film_id,
            access_token=user.access_token,
            request_id=request_id,
        )
        return await self._repository.get_film_stats(film_id)
