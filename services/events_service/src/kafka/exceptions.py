"""Исключения слоя интеграции с Kafka."""


class KafkaPublishError(Exception):
    """Базовая ошибка публикации сообщения в Kafka."""


class KafkaPublishTimeout(KafkaPublishError):
    """Kafka не подтвердила доставку сообщения за отведенное время."""


class KafkaQueueFull(KafkaPublishError):
    """Локальная очередь Kafka Producer переполнена."""


class KafkaPublisherClosed(KafkaPublishError):
    """Kafka Publisher уже завершил работу."""
