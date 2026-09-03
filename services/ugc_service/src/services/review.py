"""Бизнес-логика рецензий и голосов за них."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from auth.models import AuthenticatedUser
from core.exceptions import (
    DependencyUnavailableError,
    ResourceForbiddenError,
    ReviewNotFoundError,
)
from core.tracing import trace_method
from integrations.content import FilmCatalogService
from models.reaction import ReactionValue, ReviewReaction
from models.review import Review, ReviewDetails
from repositories.interfaces.reaction import ReviewReactionRepository
from repositories.interfaces.review import ReviewRepository

logger = logging.getLogger(__name__)


class ReviewService:
    """CRUD рецензий, агрегации и пользовательские реакции."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        reaction_repository: ReviewReactionRepository,
        film_catalog: FilmCatalogService,
    ) -> None:
        self._reviews = review_repository
        self._reactions = reaction_repository
        self._film_catalog = film_catalog

    @trace_method("ugc.reviews.create")
    async def create(
        self,
        *,
        user: AuthenticatedUser,
        film_id: UUID,
        text: str,
        request_id: str,
    ) -> ReviewDetails:
        await self._film_catalog.ensure_exists(
            film_id,
            access_token=user.access_token,
            request_id=request_id,
        )
        now = datetime.now(timezone.utc)
        review = Review(
            id=uuid4(),
            film_id=film_id,
            user_id=user.id,
            author_login=user.login,
            text=text,
            created_at=now,
            updated_at=now,
        )
        await self._reviews.create(review)
        details = await self._reviews.get_details(review.id)
        if details is None:
            raise ReviewNotFoundError
        return details

    @trace_method("ugc.reviews.get")
    async def get(self, review_id: UUID) -> ReviewDetails:
        review = await self._reviews.get_details(review_id)
        if review is None:
            raise ReviewNotFoundError
        return review

    @trace_method("ugc.reviews.list")
    async def list_by_film(
        self,
        *,
        user: AuthenticatedUser,
        film_id: UUID,
        sort: str,
        page_number: int,
        page_size: int,
        request_id: str,
    ) -> list[ReviewDetails]:
        await self._film_catalog.ensure_exists(
            film_id,
            access_token=user.access_token,
            request_id=request_id,
        )
        return await self._reviews.list_by_film(
            film_id, sort, page_number, page_size
        )

    @trace_method("ugc.reviews.update")
    async def update(
        self,
        *,
        review_id: UUID,
        user_id: UUID,
        text: str,
    ) -> ReviewDetails:
        review = await self._get_owned_review(review_id, user_id)
        await self._reviews.update_text(review.id, text)
        details = await self._reviews.get_details(review.id)
        if details is None:
            raise ReviewNotFoundError
        return details

    @trace_method("ugc.reviews.delete")
    async def delete(self, *, review_id: UUID, user_id: UUID) -> None:
        review = await self._get_owned_review(review_id, user_id)
        if not await self._reviews.delete(review.id):
            raise ReviewNotFoundError
        try:
            await self._reactions.delete_for_review(review.id)
        except DependencyUnavailableError:
            logger.warning(
                "Unable to remove orphan review reactions: review_id=%s",
                review.id,
                exc_info=True,
            )

    @trace_method("ugc.reviews.reaction.upsert")
    async def upsert_reaction(
        self,
        *,
        review_id: UUID,
        user_id: UUID,
        value: ReactionValue,
    ) -> ReviewReaction:
        if await self._reviews.get(review_id) is None:
            raise ReviewNotFoundError
        return await self._reactions.upsert(user_id, review_id, value)

    @trace_method("ugc.reviews.reaction.get")
    async def get_reaction(
        self, *, review_id: UUID, user_id: UUID
    ) -> ReviewReaction | None:
        if await self._reviews.get(review_id) is None:
            raise ReviewNotFoundError
        return await self._reactions.get(user_id, review_id)

    @trace_method("ugc.reviews.reaction.delete")
    async def delete_reaction(self, *, review_id: UUID, user_id: UUID) -> None:
        if await self._reviews.get(review_id) is None:
            raise ReviewNotFoundError
        await self._reactions.delete(user_id, review_id)

    async def _get_owned_review(
        self, review_id: UUID, user_id: UUID
    ) -> Review:
        review = await self._reviews.get(review_id)
        if review is None:
            raise ReviewNotFoundError
        if review.user_id != user_id:
            raise ResourceForbiddenError
        return review
