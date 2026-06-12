"""Модуль с декоратором backoff для повторного выполнения операций."""
import logging
import random
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from postgres_to_es.config import get_settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def backoff(
    exceptions: tuple[type[Exception], ...],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Повторяет выполнение функции с экспоненциальной задержкой."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """Оборачивает функцию в retry-логику."""

        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            """Выполняет функцию с повторным попытками."""
            attemp_number = 0
            settings = get_settings()

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    delay = min(
                        settings.backoff_border_sleep_time,
                        settings.backoff_start_sleep_time
                        * settings.backoff_factor ** attemp_number,
                    )

                    if settings.backoff_jitter:
                        delay = random.uniform(0, delay)

                    logger.exception(
                        (
                            "Function %s failed with error"
                            " %s. Retry in %.2f seconds."
                        ),
                        func.__name__,
                        error,
                        delay,
                    )

                    time.sleep(delay)
                    attemp_number += 1

        return inner

    return decorator
