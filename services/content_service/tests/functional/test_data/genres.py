"""Тестовые документы жанров."""

import uuid
from typing import Any

import pytest


@pytest.fixture(name="genre_documents", scope="session")
def genre_documents() -> list[dict[str, Any]]:
    """Формирует тестовые документы жанров."""
    return [
        {
            "uuid": str(uuid.UUID(int=number + 1)),
            "name": (
                f"Space Genre {number:02d}"
                if number % 10 == 0
                else f"Action Genre {number:02d}"
            ),
            "description": (
                f"Detective stories {number:02d}"
                if number % 10 == 0
                else f"Epic battles {number:02d}"
            ),
        }
        for number in range(60)
    ]
