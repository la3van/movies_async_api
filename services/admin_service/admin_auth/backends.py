"""Authentication backend для работы через auth-service."""
import logging
from typing import Any

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest

from admin_panel.tracing import trace_method


logger = logging.getLogger(__name__)


class AuthServiceBackend(BaseBackend):
    """Проверяет учётные данные через внешний auth-service."""
    @trace_method("admin.authenticate")
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> AbstractBaseUser | None:
        """Аутентифицирует суперпользователя через auth-service."""
        del kwargs

        if not username or not password:
            return None

        timeout = httpx.Timeout(
            connect=settings.AUTH_SERVICE_CONNECT_TIMEOUT,
            read=settings.AUTH_SERVICE_READ_TIMEOUT,
            write=settings.AUTH_SERVICE_READ_TIMEOUT,
            pool=settings.AUTH_SERVICE_CONNECT_TIMEOUT,
        )

        try:
            with httpx.Client(
                base_url=settings.AUTH_SERVICE_BASE_URL,
                timeout=timeout,
            ) as client:
                token_response = client.post(
                    "auth/login",
                    json={
                        "login": username,
                        "password": password,
                    },
                    headers=self._build_headers(request),
                )

                if token_response.status_code in {
                    400,
                    401,
                    403,
                    422,
                }:
                    return None

                token_response.raise_for_status()

                token_data = token_response.json()
                access_token = token_data.get(
                    "access_token",
                )
                refresh_token = token_data.get(
                    "refresh_token",
                )

                if not access_token:
                    logger.error(
                        "Auth-service response has no access token.",
                    )
                    return None

                profile_response = client.get(
                    "users/me",
                    headers={
                        "Authorization": (
                            f"Bearer {access_token}"
                        ),
                        **self._build_headers(request),
                    },
                )
                profile_response.raise_for_status()

                profile = profile_response.json()

                if refresh_token:
                    self._revoke_refresh_token(
                        client=client,
                        refresh_token=refresh_token,
                    )
        except (
            httpx.HTTPError,
            ValueError,
        ):
            logger.exception(
                "Unable to authenticate through auth-service.",
            )
            return None

        return self._get_or_update_shadow_user(
            profile,
        )

    @trace_method("admin.get_user")
    def get_user(
        self,
        user_id: int,
    ) -> AbstractBaseUser | None:
        """Возвращает локального shadow-пользователя по ID."""
        user_model = get_user_model()

        try:
            return user_model._default_manager.get(
                pk=user_id,
            )
        except user_model.DoesNotExist:
            return None

    @staticmethod
    def _build_headers(
        request: HttpRequest | None,
    ) -> dict[str, str]:
        """Формирует безопасные заголовки исходного запроса."""
        if request is None:
            return {}

        headers: dict[str, str] = {}

        user_agent = request.headers.get(
            "User-Agent",
        )
        request_id = request.headers.get(
            "X-Request-ID",
        )

        if user_agent:
            headers["User-Agent"] = user_agent

        if request_id:
            headers["X-Request-ID"] = request_id

        return headers

    @staticmethod
    def _revoke_refresh_token(
        client: httpx.Client,
        refresh_token: str,
    ) -> None:
        """Отзывает refresh-сессию, ненужную Django Admin."""
        try:
            response = client.post(
                "auth/logout",
                json={
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.warning(
                "Unable to revoke temporary auth refresh token.",
                exc_info=True,
            )

    @staticmethod
    def _get_or_update_shadow_user(
        profile: dict[str, Any],
    ) -> AbstractBaseUser | None:
        """Создаёт или обновляет технического пользователя Django."""
        login = profile.get(
            "login",
        )

        if not isinstance(login, str) or not login:
            logger.error(
                "Auth-service profile has no valid login.",
            )
            return None

        is_active = bool(
            profile.get(
                "is_active",
                False,
            ),
        )
        is_superuser = bool(
            profile.get(
                "is_superuser",
                False,
            ),
        )

        user_model = get_user_model()

        if not is_active or not is_superuser:
            user_model._default_manager.filter(
                username=login,
            ).update(
                is_active=is_active,
                is_staff=False,
                is_superuser=False,
            )
            return None

        user, _created = (
            user_model._default_manager.update_or_create(
                username=login,
                defaults={
                    "email": profile.get("email") or "",
                    "first_name": (
                        profile.get("first_name") or ""
                    ),
                    "last_name": (
                        profile.get("last_name") or ""
                    ),
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
        )

        if user.has_usable_password():
            user.set_unusable_password()
            user.save(
                update_fields=[
                    "password",
                ],
            )

        return user
