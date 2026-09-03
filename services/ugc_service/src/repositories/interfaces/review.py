"""Интерфейс репозитория рецензий."""

from abc import ABC, abstractmethod
from uuid import UUID

from models.review import Review, ReviewDetails


class ReviewRepository(ABC):
    """CRUD и агрегированное чтение рецензий."""

    @abstractmethod
    async def create(self, review: Review) -> Review:
        """Создать рецензию."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, review_id: UUID) -> Review | None:
        """Вернуть рецензию без агрегаций."""
        raise NotImplementedError

    @abstractmethod
    async def get_details(self, review_id: UUID) -> ReviewDetails | None:
        """Вернуть рецензию с реакциями и оценкой автора."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_film(
        self,
        film_id: UUID,
        sort: str,
        page_number: int,
        page_size: int,
    ) -> list[ReviewDetails]:
        """Вернуть страницу рецензий с гибкой сортировкой."""
        raise NotImplementedError

    @abstractmethod
    async def update_text(self, review_id: UUID, text: str) -> Review:
        """Изменить текст рецензии."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, review_id: UUID) -> bool:
        """Удалить рецензию."""
        raise NotImplementedError
