"""Тестовые документы персон."""

import random
import uuid
from typing import Any

import pytest


@pytest.fixture(name="person_documents", scope="session")
def person_documents() -> list[dict[str, Any]]:
    """Формирует тестовые документы персон."""
    rng = random.Random(42)

    return [
        {
            "uuid": str(uuid.UUID(int=person_number + 1)),
            "full_name": (
                f"Jason full_name {person_number:02d}"
                if person_number % 10 == 0
                else f"Erik full_name {person_number:02d}"
            ),
            "films": [
                {
                    "uuid": str(
                        uuid.UUID(int=person_number * 10 + film_number + 1)
                    ),
                    "roles": rng.sample(
                        ["actor", "writer", "director"],
                        k=rng.randint(1, 3),
                    ),
                }
                for film_number in range(rng.randint(1, 10))
            ],
        }
        for person_number in range(60)
    ]
