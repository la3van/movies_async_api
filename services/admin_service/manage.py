#!/usr/bin/env python
"""Утилита управления Django-проектом admin-service."""

import os
import sys


def main() -> None:
    """Запускает переданную management-команду Django."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "admin_panel.settings",
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        raise ImportError(
            "Не удалось импортировать Django. "
            "Проверьте установку зависимостей admin-service."
        ) from error

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
