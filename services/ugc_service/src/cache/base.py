"""Интерфейс простого асинхронного кеша."""

from abc import ABC, abstractmethod


class Cache(ABC):
    """Минимальный контракт кеша строковых значений."""

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Получить значение по ключу."""
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: int) -> None:
        """Сохранить значение с TTL."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удалить ключ."""
        raise NotImplementedError
