"""Интерфейс репозитория оценок."""

from abc import ABC, abstractmethod
from uuid import UUID

from models.rating import FilmRatingStats, Rating


class RatingRepository(ABC):
    """Операции хранения и агрегации пользовательских оценок."""

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, after: UUID | None, limit: int
    ) -> list[Rating]:
        """List own ratings, ordered by film UUID."""
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, user_id: UUID, film_id: UUID, value: int) -> Rating:
        """Создать или заменить оценку пользователя."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, user_id: UUID, film_id: UUID) -> Rating | None:
        """Вернуть оценку пользователя для фильма."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, film_id: UUID) -> bool:
        """Удалить оценку."""
        raise NotImplementedError

    @abstractmethod
    async def get_film_stats(self, film_id: UUID) -> FilmRatingStats:
        """Посчитать количество, среднюю оценку и распределение."""
        raise NotImplementedError
