"""Кодирование и проверка курсоров пагинации рецензий."""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from core.exceptions import InvalidPaginationCursorError


@dataclass(frozen=True, slots=True)
class ReviewCursor:
    """Позиция после последней рецензии предыдущей страницы."""

    value: datetime | int
    review_id: UUID


def encode_review_cursor(
    *,
    film_id: UUID,
    sort: str,
    value: datetime | int,
    review_id: UUID,
) -> str:
    """Сформировать непрозрачный URL-safe курсор."""
    payload = {
        "v": 1,
        "film_id": str(film_id),
        "sort": sort,
        "value": value.isoformat() if isinstance(value, datetime) else value,
        "review_id": str(review_id),
    }
    serialized = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return base64.urlsafe_b64encode(serialized).decode().rstrip("=")


def decode_review_cursor(
    cursor: str,
    *,
    film_id: UUID,
    sort: str,
) -> ReviewCursor:
    """Проверить курсор и восстановить позицию пагинации."""
    try:
        padding = "=" * (-len(cursor) % 4)
        raw_payload = base64.b64decode(
            cursor + padding,
            altchars=b"-_",
            validate=True,
        )
        payload: Any = json.loads(raw_payload)

        if not isinstance(payload, dict) or set(payload) != {
            "v",
            "film_id",
            "sort",
            "value",
            "review_id",
        }:
            raise ValueError

        if (
            payload["v"] != 1
            or payload["film_id"] != str(film_id)
            or payload["sort"] != sort
        ):
            raise ValueError

        field_name = sort.removeprefix("-")
        raw_value = payload["value"]

        if field_name in {"published_at", "updated_at"}:
            if not isinstance(raw_value, str):
                raise ValueError

            parsed_datetime = datetime.fromisoformat(raw_value)
            if parsed_datetime.tzinfo is None:
                raise ValueError

            value: datetime | int = parsed_datetime
        else:
            if isinstance(raw_value, bool) or not isinstance(raw_value, int):
                raise ValueError

            value = raw_value

        return ReviewCursor(
            value=value,
            review_id=UUID(payload["review_id"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidPaginationCursorError from error
