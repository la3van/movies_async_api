"""Auth and Profile clients with encrypted tokens and serialized refresh."""

import json
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from admin_auth.models import AuthSession


class AccessDenied(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


def encode_tokens(data: dict[str, Any]) -> str:
    tokens = {key: data[key] for key in ("access_token", "refresh_token")}
    if not all(isinstance(value, str) and value for value in tokens.values()):
        raise ServiceUnavailable
    return (
        Fernet(settings.ADMIN_TOKEN_KEY.encode())
        .encrypt(json.dumps(tokens).encode())
        .decode()
    )


def decode_tokens(record: AuthSession) -> dict[str, str]:
    try:
        data = json.loads(
            Fernet(settings.ADMIN_TOKEN_KEY.encode()).decrypt(
                record.encrypted_tokens.encode()
            )
        )
        if not isinstance(data, dict) or not all(
            isinstance(data.get(key), str)
            for key in ("access_token", "refresh_token")
        ):
            raise ValueError
        return data
    except (ValueError, InvalidToken, TypeError) as exc:
        raise AccessDenied from exc


def permissions(profile: dict[str, Any]) -> set[str]:
    try:
        return {
            str(p["code"])
            for role in profile.get("roles", [])
            for p in role["permissions"]
        }
    except (TypeError, KeyError) as exc:
        raise ServiceUnavailable from exc


def request_headers(request: HttpRequest) -> dict[str, str]:
    return {
        name: value
        for name in ("User-Agent", "X-Request-ID", "X-Real-IP")
        if (value := request.headers.get(name))
    }


def revoke(record: AuthSession) -> None:
    try:
        tokens = decode_tokens(record)
        with httpx.Client(
            base_url=settings.AUTH_SERVICE_BASE_URL, timeout=5
        ) as client:
            client.post(
                "auth/logout", json={"refresh_token": tokens["refresh_token"]}
            )
    except (httpx.HTTPError, AccessDenied):
        pass
    record.delete()


class AdminAPI:
    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    def _session(self) -> AuthSession:
        user_id = self.request.user.pk
        if user_id is None:
            raise AccessDenied
        try:
            identity = UUID(
                str(self.request.session.get("auth_session_id", ""))
            )
            record = AuthSession.objects.get(pk=identity, user_id=user_id)
        except (ValueError, AuthSession.DoesNotExist) as exc:
            raise AccessDenied from exc
        if record.expires_at <= timezone.now():
            revoke(record)
            raise AccessDenied
        return record

    def _get(
        self,
        client: httpx.Client,
        url: str,
        access: str,
        params: dict[str, str] | None,
    ) -> httpx.Response:
        return client.get(
            url,
            params=params,
            headers={
                **request_headers(self.request),
                "Authorization": "Bearer " + access,
            },
        )

    def _refresh(
        self, client: httpx.Client, record: AuthSession, used_access: str
    ) -> dict[str, str]:
        lock_id = uuid4()
        now = timezone.now()
        claimed = AuthSession.objects.filter(
            pk=record.pk, locked_until__lte=now
        ).update(locked_until=now + timedelta(seconds=30), lock_owner=lock_id)
        if not claimed:
            raise ServiceUnavailable
        try:
            record.refresh_from_db()
            tokens = decode_tokens(record)
            if tokens["access_token"] != used_access:
                return tokens
            response = client.post(
                settings.AUTH_SERVICE_BASE_URL + "auth/refresh",
                json={"refresh_token": tokens["refresh_token"]},
                headers=request_headers(self.request),
            )
            if response.status_code in {400, 401, 403}:
                record.delete()
                raise AccessDenied
            if response.status_code != 200:
                raise ServiceUnavailable
            record.encrypted_tokens = encode_tokens(response.json())
            record.save(update_fields=["encrypted_tokens"])
            return decode_tokens(record)
        finally:
            AuthSession.objects.filter(
                pk=record.pk, lock_owner=lock_id
            ).update(locked_until=timezone.now(), lock_owner=None)

    def get(
        self,
        path: str,
        *,
        profile: bool = False,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        record = self._session()
        tokens = decode_tokens(record)
        base = (
            settings.PROFILE_SERVICE_BASE_URL
            if profile
            else settings.AUTH_SERVICE_BASE_URL
        )
        url = base.rstrip("/") + "/" + path.lstrip("/")
        try:
            with httpx.Client(timeout=5, follow_redirects=False) as client:
                response = self._get(
                    client, url, tokens["access_token"], params
                )
                if response.status_code == 401:
                    tokens = self._refresh(
                        client, record, tokens["access_token"]
                    )
                    response = self._get(
                        client, url, tokens["access_token"], params
                    )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ServiceUnavailable from exc
        if response.status_code in {401, 403}:
            raise AccessDenied
        if response.status_code not in {200, 404}:
            raise ServiceUnavailable
        return response

    def current_user(self) -> dict[str, Any]:
        response = self.get("users/me")
        try:
            data = response.json()
            expected = self._session().external_user_id
            if (
                response.status_code != 200
                or UUID(data["id"]) != expected
                or data["is_active"] is not True
            ):
                raise AccessDenied
            if not isinstance(data["is_superuser"], bool):
                raise ServiceUnavailable
            return data
        except (ValueError, KeyError, TypeError) as exc:
            raise ServiceUnavailable from exc
