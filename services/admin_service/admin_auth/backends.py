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

    INVALID_CREDENTIAL_STATUS_CODES = frozenset(
        {
            400,
            401,
            403,
            422,
        },
    )

    @trace_method("admin.authenticate")
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> AbstractBaseUser | None:
        """
        Аутентифицирует администратора через auth-service.

        Auth-service проверяет пароль и выдаёт временную пару
        токенов. Admin-service получает профиль пользователя,
        проверяет административные права и создаёт локальную
        Django-сессию.

        Refresh-токен используется только во время этого процесса
        и отзывается независимо от результата получения профиля.
        """
        del kwargs

        if not username or not password:
            return None

        request_headers = self._build_headers(request)
        refresh_token: str | None = None
        profile: dict[str, Any] | None = None

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
                try:
                    token_response = client.post(
                        "auth/login",
                        json={
                            "login": username,
                            "password": password,
                        },
                        headers=request_headers,
                    )

                    if (
                        token_response.status_code
                        in self.INVALID_CREDENTIAL_STATUS_CODES
                    ):
                        return None

                    token_response.raise_for_status()

                    token_data = self._read_json_object(
                        response=token_response,
                        response_name="login",
                    )

                    access_token = self._read_required_string(
                        data=token_data,
                        field_name="access_token",
                        response_name="login",
                    )

                    refresh_token = self._read_required_string(
                        data=token_data,
                        field_name="refresh_token",
                        response_name="login",
                    )

                    profile_response = client.get(
                        "users/me",
                        headers={
                            **request_headers,
                            "Authorization": (
                                f"Bearer {access_token}"
                            ),
                        },
                    )

                    profile_response.raise_for_status()

                    profile = self._read_json_object(
                        response=profile_response,
                        response_name="users/me",
                    )
                finally:
                    if refresh_token is not None:
                        self._revoke_refresh_token(
                            client=client,
                            refresh_token=refresh_token,
                            headers=request_headers,
                        )

        except httpx.TimeoutException:
            logger.warning(
                "Auth-service request timed out.",
                exc_info=True,
            )
            return None

        except httpx.HTTPStatusError as error:
            logger.warning(
                (
                    "Auth-service returned HTTP status %s "
                    "for request %s."
                ),
                error.response.status_code,
                error.request.url,
                exc_info=True,
            )
            return None

        except httpx.HTTPError:
            logger.exception(
                "Auth-service request failed.",
            )
            return None

        except (TypeError, ValueError):
            logger.exception(
                "Auth-service returned an invalid response.",
            )
            return None

        if profile is None:
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
        """
        Формирует заголовки для запросов в auth-service.

        X-Request-ID используется для корреляции логов и трассировки.
        X-Real-IP передаёт auth-service адрес исходного пользователя,
        а не адрес Docker-контейнера admin-service.
        """
        if request is None:
            return {}

        headers: dict[str, str] = {}

        forwarded_headers = {
            "User-Agent": request.headers.get(
                "User-Agent",
            ),
            "X-Request-ID": request.headers.get(
                "X-Request-ID",
            ),
            "X-Real-IP": request.headers.get(
                "X-Real-IP",
            ),
        }

        for header_name, header_value in forwarded_headers.items():
            if header_value:
                headers[header_name] = header_value

        return headers

    @staticmethod
    def _read_json_object(
        response: httpx.Response,
        response_name: str,
    ) -> dict[str, Any]:
        """Читает JSON-объект из ответа auth-service."""
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                (
                    f"Auth-service {response_name} response "
                    "must be a JSON object."
                ),
            )

        return data

    @staticmethod
    def _read_required_string(
        data: dict[str, Any],
        field_name: str,
        response_name: str,
    ) -> str:
        """Получает обязательную непустую строку из ответа."""
        value = data.get(
            field_name,
        )

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                (
                    f"Auth-service {response_name} response "
                    f"has no valid {field_name}."
                ),
            )

        return value

    @staticmethod
    def _revoke_refresh_token(
        client: httpx.Client,
        refresh_token: str,
        headers: dict[str, str],
    ) -> None:
        """
        Отзывает временную refresh-сессию Django Admin.

        Ошибка logout не должна отменять успешную авторизацию:
        отзыв выполняется в режиме best effort.
        """
        try:
            response = client.post(
                "auth/logout",
                json={
                    "refresh_token": refresh_token,
                },
                headers=headers,
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
        """
        Создаёт или обновляет технического пользователя Django.

        Shadow-user нужен Django только для request.user,
        permissions административной панели и локальной сессии.
        Настоящий пароль в Admin Service не хранится.
        """
        login = profile.get(
            "login",
        )
        is_active = profile.get(
            "is_active",
        )
        is_superuser = profile.get(
            "is_superuser",
        )

        if not isinstance(login, str) or not login.strip():
            logger.error(
                "Auth-service profile has no valid login.",
            )
            return None

        if not isinstance(is_active, bool):
            logger.error(
                "Auth-service profile has invalid is_active.",
            )
            return None

        if not isinstance(is_superuser, bool):
            logger.error(
                "Auth-service profile has invalid is_superuser.",
            )
            return None

        email = profile.get(
            "email",
        )
        first_name = profile.get(
            "first_name",
        )
        last_name = profile.get(
            "last_name",
        )

        if not isinstance(email, str):
            logger.error(
                "Auth-service profile has invalid email.",
            )
            return None

        if first_name is not None and not isinstance(
            first_name,
            str,
        ):
            logger.error(
                "Auth-service profile has invalid first_name.",
            )
            return None

        if last_name is not None and not isinstance(
            last_name,
            str,
        ):
            logger.error(
                "Auth-service profile has invalid last_name.",
            )
            return None

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
                    "email": email,
                    "first_name": first_name or "",
                    "last_name": last_name or "",
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
