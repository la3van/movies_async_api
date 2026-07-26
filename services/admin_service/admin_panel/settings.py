"""Настройки Django-проекта admin-service."""
import os
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def get_required_env(name: str) -> str:
    """Возвращает обязательную переменную окружения."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ImproperlyConfigured(
            f"Environment variable {name!r} is required.",
        )

    return value.strip()


def get_bool_env(
    name: str,
    default: bool = False,
) -> bool:
    """Преобразует переменную окружения в bool."""
    value = os.getenv(name, str(default))

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_int_env(
    name: str,
    default: int,
) -> int:
    """Преобразует переменную окружения в int."""
    value = os.getenv(name, str(default))

    try:
        return int(value)
    except ValueError as error:
        raise ImproperlyConfigured(
            f"Environment variable {name!r} must be an integer.",
        ) from error


def get_list_env(
    name: str,
    default: str = "",
) -> list[str]:
    """Преобразует строку с запятыми в список значений."""
    value = os.getenv(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


PROJECT_NAME = os.getenv(
    "PROJECT_NAME",
    "admin-service",
)

SECRET_KEY = get_required_env(
    "SECRET_KEY",
)

DEBUG = get_bool_env(
    "DEBUG",
    False,
)

ENABLE_DEBUG_TOOLBAR = (
    DEBUG
    and get_bool_env(
        "ENABLE_DEBUG_TOOLBAR",
        False,
    )
)

ALLOWED_HOSTS = get_list_env(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,admin-service",
)

CSRF_TRUSTED_ORIGINS = get_list_env(
    "CSRF_TRUSTED_ORIGINS",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "admin_auth.apps.AdminAuthConfig",
    "content.apps.ContentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS.append(
        "debug_toolbar",
    )

    MIDDLEWARE.insert(
        2,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": (
            "admin_panel.debug_toolbar.show_toolbar"
        ),
    }

ROOT_URLCONF = "admin_panel.urls"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth.context_processors."
                    "auth"
                ),
                (
                    "django.contrib.messages.context_processors."
                    "messages"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "admin_panel.wsgi.application"
ASGI_APPLICATION = "admin_panel.asgi.application"


# Служебная база Django Admin:
# сессии, shadow-пользователи и журнал действий.
SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    str(BASE_DIR / "data" / "admin.sqlite3"),
)

POSTGRES_OPTIONS = os.getenv(
    "POSTGRES_OPTIONS",
    "-c search_path=public,content",
).strip()

POSTGRES_STATEMENT_TIMEOUT_MS = get_int_env(
    "POSTGRES_STATEMENT_TIMEOUT_MS",
    30_000,
)

postgres_connection_options: dict[str, Any] = {
    "connect_timeout": get_int_env(
        "POSTGRES_CONNECT_TIMEOUT",
        5,
    ),
}

postgres_options_parts = [
    POSTGRES_OPTIONS,
    (
        "-c statement_timeout="
        f"{POSTGRES_STATEMENT_TIMEOUT_MS}"
    ),
]

postgres_connection_options["options"] = " ".join(
    option
    for option in postgres_options_parts
    if option
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_PATH,
        "OPTIONS": {
            "timeout": 20,
        },
    },
    "content": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv(
            "POSTGRES_HOST",
            "theatre-db",
        ),
        "PORT": get_int_env(
            "POSTGRES_PORT",
            5432,
        ),
        "NAME": os.getenv(
            "POSTGRES_DB",
            "theatre",
        ),
        "USER": os.getenv(
            "POSTGRES_USER",
            "postgres",
        ),
        "PASSWORD": get_required_env(
            "POSTGRES_PASSWORD",
        ),
        "OPTIONS": postgres_connection_options,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    },
}

DATABASE_ROUTERS = [
    "content.router.ContentDatabaseRouter",
]

AUTHENTICATION_BACKENDS = [
    "admin_auth.backends.AuthServiceBackend",
]

# Локальные пароли не используются:
# пароль всегда проверяет auth-service.
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE = os.getenv(
    "LANGUAGE_CODE",
    "en-us",
)

TIME_ZONE = os.getenv(
    "TIME_ZONE",
    "UTC",
)

USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = get_int_env(
    "SESSION_COOKIE_AGE",
    900,
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AUTH_SERVICE_HOST = os.getenv(
    "AUTH_SERVICE_HOST",
    "auth-service",
)

AUTH_SERVICE_PORT = get_int_env(
    "AUTH_SERVICE_PORT",
    8000,
)

AUTH_SERVICE_API_PREFIX = os.getenv(
    "AUTH_SERVICE_API_PREFIX",
    "/api/v1",
).strip("/")

AUTH_SERVICE_BASE_URL = (
    f"http://{AUTH_SERVICE_HOST}:{AUTH_SERVICE_PORT}/"
    f"{AUTH_SERVICE_API_PREFIX}/"
)

AUTH_SERVICE_CONNECT_TIMEOUT = get_int_env(
    "AUTH_SERVICE_CONNECT_TIMEOUT",
    1,
)

AUTH_SERVICE_READ_TIMEOUT = get_int_env(
    "AUTH_SERVICE_READ_TIMEOUT",
    2,
)
