"""Интерфейс выполнения операций с повторными попытками."""
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

ResultType = TypeVar('ResultType')


class RetryExecutor(ABC):
    """Выполняет операцию повторно при заданных исключениях."""
    @abstractmethod
    def execute(
        self,
        operation: Callable[[], ResultType],
        exceptions: tuple[type[Exception], ...],
    ) -> ResultType:
        """Выполняет операцию с повторынми попытками."""
        pass  # pragma: no cover
