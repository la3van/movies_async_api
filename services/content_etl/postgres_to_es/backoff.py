"""Повторное выполнение операций с экспоненциальной задержкой."""
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import (
    Concatenate,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
)

from postgres_to_es.interfaces import RetryExecutor

logger = logging.getLogger(__name__)

Parameters = ParamSpec('Parameters')
ResultType = TypeVar('ResultType')


class SupportsRetry(Protocol):
    """Объект, содержащий исполнитель повторных попыток."""
    _retry_executor: RetryExecutor


OwnerType = TypeVar(
    'OwnerType',
    bound=SupportsRetry,
)


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    """Настройки экспоненциальной задержки."""
    start_sleep_time: float
    factor: float
    max_sleep_time: float
    jitter: bool

    def __post_init__(self) -> None:
        """Проверяет корректность настроек."""
        if self.start_sleep_time < 0:
            raise ValueError(
                'Начальная задержка не может быть отрицательной.',
            )

        if self.factor < 1:
            raise ValueError(
                'Множитель backoff должен быть не меньше 1.',
            )

        if self.max_sleep_time < self.start_sleep_time:
            raise ValueError(
                'Максимальная задержка не может быть '
                'меньше начальной.',
            )


class BackoffRetryExecutor(RetryExecutor):
    """Выполняет операции с экспоненциальной задержкой."""
    def __init__(
        self,
        policy: BackoffPolicy,
        sleeper: Callable[[float], None] = time.sleep,
        randomizer: Callable[
            [float, float],
            float,
        ] = random.uniform,
    ) -> None:
        """Инициализирует executor с политикой ожидания и
        функциями задержки."""
        self._policy = policy
        self._sleeper = sleeper
        self._randomizer = randomizer

    def execute(
        self,
        operation: Callable[[], ResultType],
        exceptions: tuple[type[Exception], ...],
    ) -> ResultType:
        """Повторяет операцию при указанных исключениях."""
        attempt_number = 0

        while True:
            try:
                return operation()
            except exceptions as error:
                delay = min(
                    self._policy.max_sleep_time,
                    (
                        self._policy.start_sleep_time
                        * self._policy.factor ** attempt_number
                    ),
                )

                if self._policy.jitter:
                    delay = self._randomizer(
                        0.0,
                        delay,
                    )

                logger.warning(
                    (
                        'Operation %s failed: %s. '
                        'Retry in %.2f seconds.'
                    ),
                    getattr(
                        operation,
                        '__name__',
                        operation.__class__.__name__,
                    ),
                    error,
                    delay,
                    exc_info=True,
                )

                self._sleeper(delay)
                attempt_number += 1


def retryable(
    *,
    exceptions: tuple[type[Exception], ...],
) -> Callable[
    [
        Callable[
            Concatenate[
                OwnerType,
                Parameters,
            ],
            ResultType,
        ],
    ],
    Callable[
        Concatenate[
            OwnerType,
            Parameters,
        ],
        ResultType,
    ],
]:
    """Повторяет метод через executor, внедрённый в объект."""
    def decorator(
        function: Callable[
            Concatenate[
                OwnerType,
                Parameters,
            ],
            ResultType,
        ],
    ) -> Callable[
        Concatenate[
            OwnerType,
            Parameters,
        ],
        ResultType,
    ]:
        @wraps(function)
        def wrapper(
            self: OwnerType,
            /,
            *args: Parameters.args,
            **kwargs: Parameters.kwargs,
        ) -> ResultType:
            return self._retry_executor.execute(
                operation=lambda: function(
                    self,
                    *args,
                    **kwargs,
                ),
                exceptions=exceptions,
            )

        return cast(
            Callable[
                Concatenate[
                    OwnerType,
                    Parameters,
                ],
                ResultType,
            ],
            wrapper,
        )

    return decorator
