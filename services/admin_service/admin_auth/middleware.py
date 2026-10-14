"""Revalidate every admin request so revoked staff rights stop working."""

from collections.abc import Callable
from typing import cast

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from admin_auth.client import (
    AccessDenied,
    AdminAPI,
    ServiceUnavailable,
    permissions,
)


class ProfileRequest(HttpRequest):
    """Запрос админки с проверенными разрешениями на чтение профилей."""

    profile_permissions: set[str]


class RefreshAuthMiddleware:
    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse]
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            request.path.startswith("/admin/")
            and request.user.is_authenticated
            and request.path not in {"/admin/login/", "/admin/logout/"}
        ):
            try:
                profile = AdminAPI(request).current_user()
                grants = permissions(profile)
                superuser = profile["is_superuser"] is True
                if not superuser and "profiles:read" not in grants:
                    raise AccessDenied
            except AccessDenied:
                logout(request)
                return redirect("admin:login")
            except ServiceUnavailable:
                return HttpResponse(
                    "Auth service is temporarily unavailable.", status=503
                )
            request.user.is_staff = True
            request.user.is_superuser = superuser
            cast(ProfileRequest, request).profile_permissions = grants
        return self.get_response(request)
