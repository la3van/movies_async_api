"""Read-only profile pages integrated into the existing Django Admin."""

from typing import Any
from uuid import UUID

from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import URLPattern, URLResolver, path, reverse

from admin_auth.client import AccessDenied, AdminAPI, ServiceUnavailable


def can_read(request: HttpRequest) -> bool:
    return request.user.is_superuser or "profiles:read" in getattr(
        request, "profile_permissions", set()
    )


class ProfileAdminSite(AdminSite):
    def get_urls(self) -> list[URLPattern | URLResolver]:
        return [
            path(
                "profiles/",
                self.admin_view(self.profiles),
                name="profiles_list",
            ),
            path(
                "profiles/<uuid:user_id>/",
                self.admin_view(self.profile),
                name="profiles_detail",
            ),
        ] + super().get_urls()

    def get_app_list(
        self, request: HttpRequest, app_label: str | None = None
    ) -> list[dict[str, Any]]:
        apps = super().get_app_list(request, app_label)
        if can_read(request) and app_label in {None, "profiles"}:
            apps.append(
                {
                    "name": "Пользователи",
                    "app_label": "profiles",
                    "app_url": reverse("admin:profiles_list"),
                    "has_module_perms": True,
                    "models": [
                        {
                            "name": "Профили",
                            "object_name": "Profile",
                            "perms": {
                                "view": True,
                                "change": False,
                                "add": False,
                                "delete": False,
                            },
                            "admin_url": reverse("admin:profiles_list"),
                            "add_url": None,
                            "view_only": True,
                        }
                    ],
                }
            )
        return apps

    def profiles(self, request: HttpRequest) -> HttpResponse:
        if not can_read(request):
            raise PermissionDenied
        params = {"limit": "50"}
        try:
            if request.GET.get("after"):
                params["after"] = str(UUID(request.GET["after"]))
            if request.GET.get("user_id"):
                identity = UUID(request.GET["user_id"])
                from django.shortcuts import redirect

                return redirect("admin:profiles_detail", user_id=identity)
        except ValueError:
            return HttpResponse("Invalid UUID", status=400)
        try:
            response = AdminAPI(request).get(
                "profiles/", profile=True, params=params
            )
            data = response.json()
            if not isinstance(data, dict) or not isinstance(
                data.get("items"), list
            ):
                raise ServiceUnavailable
        except AccessDenied as exc:
            raise PermissionDenied from exc
        except (ServiceUnavailable, ValueError):
            return HttpResponse(
                "Profile service is temporarily unavailable.", status=503
            )
        return TemplateResponse(
            request,
            "admin/profiles/list.html",
            {
                **self.each_context(request),
                "title": "Профили пользователей",
                "items": data["items"],
                "next_cursor": data.get("next_cursor"),
            },
        )

    def profile(self, request: HttpRequest, user_id: UUID) -> HttpResponse:
        if not can_read(request):
            raise PermissionDenied
        try:
            response = AdminAPI(request).get(
                f"profiles/{user_id}", profile=True
            )
            if response.status_code == 404:
                raise Http404
            data = response.json()
            if UUID(data["user_id"]) != user_id:
                raise ServiceUnavailable
        except AccessDenied as exc:
            raise PermissionDenied from exc
        except (ServiceUnavailable, ValueError, KeyError, TypeError):
            return HttpResponse(
                "Profile service is temporarily unavailable.", status=503
            )
        fields = [
            ("UUID пользователя", data["user_id"]),
            ("Имя", data.get("first_name")),
            ("Фамилия", data.get("last_name")),
            ("Отчество", data.get("middle_name")),
            ("Телефон", data.get("phone")),
            (
                "Подтверждение телефона",
                data.get("phone_verified_at") or "Не подтверждён",
            ),
            (
                "Согласие на маркетинг",
                "Да" if data.get("marketing_consent") else "Нет",
            ),
            ("Создан", data.get("created_at")),
            ("Обновлён", data.get("updated_at")),
        ]
        return TemplateResponse(
            request,
            "admin/profiles/detail.html",
            {
                **self.each_context(request),
                "title": "Профиль пользователя",
                "fields": fields,
            },
        )
