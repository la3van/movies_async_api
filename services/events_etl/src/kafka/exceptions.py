"""Исключения слоя интеграции ETL-сервиса с Kafka."""


class KafkaConsumerError(Exception):
    """Базовая ошибка Kafka Consumer."""


class KafkaConsumeError(KafkaConsumerError):
    """Ошибка получения сообщений из Kafka."""


class KafkaCommitError(KafkaConsumerError):
    """Ошибка подтверждения обработанных Kafka offsets."""


class KafkaConsumerClosed(KafkaConsumerError):
    """Kafka Consumer уже завершил работу."""


class KafkaDeadLetterPublishError(Exception):
    """Ошибка публикации некорректного события в Kafka DLQ."""
