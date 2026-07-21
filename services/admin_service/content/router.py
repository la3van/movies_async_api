"""Маршрутизация моделей контента в theatre-db."""
from typing import Any


class ContentDatabaseRouter:
    """Направляет модели приложения content в PostgreSQL."""
    app_label = "content"
    database_alias = "content"

    def db_for_read(
        self,
        model: type,
        **hints: Any,
    ) -> str | None:
        """Выбирает базу для чтения модели."""
        del hints

        if model._meta.app_label == self.app_label:
            return self.database_alias

        return None

    def db_for_write(
        self,
        model: type,
        **hints: Any,
    ) -> str | None:
        """Выбирает базу для записи модели."""
        del hints

        if model._meta.app_label == self.app_label:
            return self.database_alias

        return None

    def allow_relation(
        self,
        obj1: Any,
        obj2: Any,
        **hints: Any,
    ) -> bool | None:
        """Разрешает связи между моделями одной контентной базы."""
        del hints

        obj1_is_content = (
            obj1._meta.app_label == self.app_label
        )
        obj2_is_content = (
            obj2._meta.app_label == self.app_label
        )

        if obj1_is_content or obj2_is_content:
            return obj1_is_content and obj2_is_content

        return None

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool | None:
        """Запрещает Django управлять таблицами content."""
        del model_name
        del hints

        if db == self.database_alias:
            return False

        if app_label == self.app_label:
            return False

        return None
