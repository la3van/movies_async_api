"""Абстракция кеша приложения."""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

ModelType = TypeVar('ModelType', bound=BaseModel)


class Cache(ABC):
    """Определяет контракт кеширования Pydantic-моделей."""
    @abstractmethod
    async def get_model(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> ModelType | None:
        """Возвращает одну модель из кеша или None, если значение
        отсутствует."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_models(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> list[ModelType] | None:
        """Возвращает список моделей из кеша или None, если значение
        отсутствует."""
        pass  # pragma: no cover

    @abstractmethod
    async def set_model(
        self,
        key: str,
        value: BaseModel,
        ttl: int,
    ) -> None:
        """Сохраняет одну модель в кеше на заданное время."""
        pass  # pragma: no cover

    @abstractmethod
    async def set_models(
        self,
        key: str,
        values: Sequence[BaseModel],
        ttl: int,
    ) -> None:
        """Сохраняет последовательность моделей в кеше на заданное время."""
        pass  # pragma: no cover

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удаляет значение из кеша."""
        pass  # pragma: no cover

    @abstractmethod
    async def delete_many(self, keys: Sequence[str]) -> None:
        """Удаляет несколько значений из кеша."""
        pass  # pragma: no cover

    @abstractmethod
    async def delete_by_pattern(self, pattern: str) -> None:
        """Удаляет значения из кеша по шаблону ключа."""
        pass  # pragma: no cover
