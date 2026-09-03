"""WSGI-конфигурация admin-service."""

import os

from django.core.wsgi import get_wsgi_application

from admin_panel.tracing import configure_tracing

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "admin_panel.settings",
)

configure_tracing(
    default_service_name="admin-service",
)

application = get_wsgi_application()
