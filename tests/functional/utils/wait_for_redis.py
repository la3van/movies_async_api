"""Ожидание готовности Redis перед тестами."""
import time

from redis import Redis
from redis.exceptions import ConnectionError, TimeoutError

from tests.functional.settings import test_settings


def wait_for_redis() -> None:
    deadline = time.monotonic() + test_settings.redis_wait_timeout

    with Redis.from_url(
        test_settings.redis_url,
        socket_connect_timeout=(
            test_settings.redis_socket_connect_timeout
        ),
        socket_timeout=test_settings.redis_socket_timeout,
    ) as redis_client:
        while time.monotonic() < deadline:
            try:
                if redis_client.ping():
                    return
            except (ConnectionError, TimeoutError):
                pass

            time.sleep(test_settings.redis_wait_interval)

    raise RuntimeError(
        'Redis did not become available within '
        f'{test_settings.redis_wait_timeout} seconds.',
    )


if __name__ == '__main__':
    wait_for_redis()
