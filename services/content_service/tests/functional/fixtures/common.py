"""Общие системные фикстуры функциональных тестов."""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Создаёт отдельный event loop на время тестовой сессии."""
    loop = asyncio.new_event_loop()

    yield loop

    loop.close()
