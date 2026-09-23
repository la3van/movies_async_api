"""Жизненный цикл фоновых процессов и обработка завершения."""

import asyncio
import signal
from collections.abc import Awaitable, Callable

from core.config import get_settings
from core.health import HealthServer


async def supervise(run: Callable[[asyncio.Event], Awaitable[None]]) -> None:
    """SIGTERM сначала завершает текущую транзакцию; затем даёт выйти."""
    from core.telemetry import configure, shutdown

    configure(get_settings())
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    health = HealthServer(get_settings().health_stale_seconds)
    try:
        await run(stop)
    finally:
        await asyncio.to_thread(health.close)
        await asyncio.to_thread(shutdown)


async def pause(stop: asyncio.Event, seconds: float) -> None:
    """Ожидает следующую итерацию с прерыванием по сигналу остановки."""
    try:
        await asyncio.wait_for(stop.wait(), seconds)
    except asyncio.TimeoutError:
        pass
