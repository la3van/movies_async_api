"""Вспомогательные функции функциональных тестов."""

from typing import Any


def build_auth_headers(access_token: str) -> dict[str, str]:
    """Возвращает Authorization headers для access-токена."""
    return {
        "Authorization": f"Bearer {access_token}",
    }


def assert_has_fields(data: dict[str, Any], fields: set[str]) -> None:
    """Проверяет, что в словаре есть ожидаемые поля."""
    missing_fields = fields - set(data)

    assert not missing_fields, f"Missing fields: {missing_fields}"


def assert_token_pair_response(data: dict[str, Any]) -> None:
    """Проверяет базовую структуру ответа с парой токенов."""
    assert_has_fields(
        data,
        {
            "access_token",
            "refresh_token",
            "token_type",
        },
    )

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert data["token_type"] == "bearer"


def get_response_detail(data: dict[str, Any]) -> str | list[Any] | None:
    """Возвращает поле detail из error-response."""
    return data.get("detail")
