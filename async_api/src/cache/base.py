from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

ModelType = TypeVar('ModelType', bound=BaseModel)


class Cache(ABC):
    @abstractmethod
    async def get_model(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> ModelType | None:
        pass  # pragma: no cover

    @abstractmethod
    async def get_models(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> list[ModelType] | None:
        pass  # pragma: no cover

    @abstractmethod
    async def set_model(
        self,
        key: str,
        value: BaseModel,
        ttl: int,
    ) -> None:
        pass  # pragma: no cover

    @abstractmethod
    async def set_models(
        self,
        key: str,
        values: Sequence[BaseModel],
        ttl: int,
    ) -> None:
        pass  # pragma: no cover
