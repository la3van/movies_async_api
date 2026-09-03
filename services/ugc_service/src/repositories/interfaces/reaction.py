"""Интерфейс репозитория реакций на рецензии."""

from abc import ABC, abstractmethod
from uuid import UUID

from models.reaction import ReactionValue, ReviewReaction


class ReviewReactionRepository(ABC):
    """Операции с лайками и дизлайками рецензий."""

    @abstractmethod
    async def upsert(
        self,
        user_id: UUID,
        review_id: UUID,
        value: ReactionValue,
    ) -> ReviewReaction:
        """Создать или заменить голос пользователя."""
        raise NotImplementedError

    @abstractmethod
    async def get(
        self, user_id: UUID, review_id: UUID
    ) -> ReviewReaction | None:
        """Вернуть голос текущего пользователя."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, review_id: UUID) -> bool:
        """Удалить голос пользователя."""
        raise NotImplementedError

    @abstractmethod
    async def delete_for_review(self, review_id: UUID) -> None:
        """Удалить все голоса удаляемой рецензии."""
        raise NotImplementedError
