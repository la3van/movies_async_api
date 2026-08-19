"""Исключения слоя интеграции с ClickHouse."""


class ClickHouseStorageError(Exception):
    """Базовая ошибка работы с ClickHouse."""


class ClickHouseInsertError(ClickHouseStorageError):
    """Ошибка записи пакета событий в ClickHouse."""


class ClickHouseUnavailable(ClickHouseStorageError):
    """ClickHouse временно недоступен."""


class ClickHouseStorageClosed(ClickHouseStorageError):
    """Клиент ClickHouse уже завершил работу."""
