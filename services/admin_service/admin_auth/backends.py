"""Authenticate staff with Auth; retain encrypted session credentials."""

from datetime import timedelta
from typing import Any
from uuid import UUID

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils import timezone

from admin_auth.client import (
    ServiceUnavailable,
    encode_tokens,
    permissions,
    request_headers,
)
from admin_auth.models import AuthSession


class AuthServiceBackend(BaseBackend):
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        if request is None or not username or not password:
            return None
        refresh_token = None
        accepted = False
        try:
            with httpx.Client(
                base_url=settings.AUTH_SERVICE_BASE_URL, timeout=5
            ) as client:
                try:
                    response = client.post(
                        "auth/login",
                        json={"login": username, "password": password},
                        headers=request_headers(request),
                    )
                    if response.status_code != 200:
                        return None
                    tokens = response.json()
                    refresh_token = tokens["refresh_token"]
                    response = client.get(
                        "users/me",
                        headers={
                            **request_headers(request),
                            "Authorization": "Bearer "
                            + tokens["access_token"],
                        },
                    )
                    if response.status_code != 200:
                        return None
                    profile = response.json()
                    identity = UUID(profile["id"])
                    superuser = profile.get("is_superuser") is True
                    if profile.get("is_active") is not True or not (
                        superuser or "profiles:read" in permissions(profile)
                    ):
                        return None
                    encrypted = encode_tokens(tokens)
                    user, _ = get_user_model().objects.update_or_create(
                        username=str(identity),
                        defaults={
                            "is_active": True,
                            "is_staff": True,
                            "is_superuser": superuser,
                            "first_name": "",
                            "last_name": "",
                            "email": "",
                        },
                    )
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                    record = AuthSession.objects.create(
                        user=user,
                        external_user_id=identity,
                        encrypted_tokens=encrypted,
                        expires_at=timezone.now()
                        + timedelta(seconds=settings.SESSION_COOKIE_AGE),
                    )
                    request.session["auth_session_id"] = str(record.pk)
                    accepted = True
                    return user
                finally:
                    if refresh_token and not accepted:
                        client.post(
                            "auth/logout",
                            json={"refresh_token": refresh_token},
                        )
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            ServiceUnavailable,
        ):
            return None

    def get_user(self, user_id: int) -> User | None:
        return (
            get_user_model().objects.filter(pk=user_id, is_active=True).first()
        )
