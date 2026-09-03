"""Общие HTTP-операции OAuth-провайдеров."""

from typing import Any

import httpx
from services.exceptions import (
    OAuthProviderResponseError,
    OAuthProviderUnavailableError,
)


async def request_oauth_json(
    *,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    service_name: str,
    **request_kwargs: Any,
) -> dict[str, Any]:
    """Выполняет OAuth-запрос и возвращает JSON-объект."""
    try:
        response = await client.request(
            method=method,
            url=url,
            **request_kwargs,
        )
    except httpx.RequestError as error:
        raise OAuthProviderUnavailableError(
            f"{service_name} is unavailable",
        ) from error

    if response.is_server_error:
        raise OAuthProviderUnavailableError(
            f"{service_name} returned a server error",
        )

    if response.is_client_error or response.is_redirect:
        raise OAuthProviderResponseError(
            f"{service_name} rejected the request",
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise OAuthProviderResponseError(
            f"{service_name} returned invalid JSON",
        ) from error

    if not isinstance(payload, dict):
        raise OAuthProviderResponseError(
            f"{service_name} returned an invalid response",
        )

    if "error" in payload:
        raise OAuthProviderResponseError(
            f"{service_name} returned an OAuth error",
        )

    return payload
