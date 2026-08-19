"""Исключения сервисного слоя ETL-процесса."""


class EventMappingError(Exception):
    """Ошибка преобразования Kafka-события в строку ClickHouse."""


class ETLProcessingError(Exception):
    """Критическая ошибка обработки пользовательских событий."""
