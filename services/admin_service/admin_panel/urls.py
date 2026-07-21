"""Маршруты Django-проекта admin-service."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path


admin.site.site_header = settings.PROJECT_NAME
admin.site.site_title = settings.PROJECT_NAME
admin.site.index_title = "Управление контентом"

urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
]

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns.append(
        path(
            "__debug__/",
            include(debug_toolbar.urls),
        ),
    )
