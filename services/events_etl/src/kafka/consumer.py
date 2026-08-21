"""Чтение пользовательских событий из Kafka и управление offsets."""
import logging

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    TopicPartition,
)

from core.config import Settings
from kafka.base import ConsumedMessage
from kafka.exceptions import (
    KafkaCommitError,
    KafkaConsumeError,
    KafkaConsumerClosed,
)

logger = logging.getLogger(__name__)


class KafkaBatchConsumer:
    """Получает пользовательские события из Kafka пакетами."""
    def __init__(
        self,
        settings: Settings,
        consumer: Consumer | None = None,
    ) -> None:
        """Создать Kafka Consumer."""
        self._settings = settings
        self._topic = settings.kafka_topic

        self._consumer = (
            consumer
            or Consumer(settings.kafka_consumer_config)
        )

        self._subscribed = False
        self._closed = False

    def subscribe(self) -> None:
        """Подписать Consumer на топик пользовательских событий."""
        self._ensure_open()

        if self._subscribed:
            return

        try:
            self._consumer.subscribe(
                [
                    self._topic,
                ]
            )
        except KafkaException as exc:
            raise KafkaConsumeError(
                f"Не удалось подписаться на Kafka topic "
                f"{self._topic}"
            ) from exc

        self._subscribed = True

        logger.info(
            "Kafka Consumer подписан на topic=%s",
            self._topic,
        )

    def poll_batch(self) -> list[ConsumedMessage]:
        """Получить очередной пакет сообщений из Kafka."""
        self._ensure_open()

        if not self._subscribed:
            raise KafkaConsumeError(
                "Kafka Consumer не подписан на topic"
            )

        try:
            messages = self._consumer.consume(
                num_messages=(
                    self._settings.kafka_batch_size
                ),
                timeout=(
                    self._settings.kafka_poll_timeout_seconds
                ),
            )
        except (KafkaException, RuntimeError) as exc:
            raise KafkaConsumeError(
                "Не удалось получить сообщения из Kafka: "
                f"{exc}"
            ) from exc

        if not messages:
            return []

        result: list[ConsumedMessage] = []
        for message in messages:
            if self._is_partition_eof(message):
                continue

            error = message.error()

            if error is not None:
                raise KafkaConsumeError(
                    "Ошибка Kafka message: "
                    f"{error}"
                )

            result.append(
                ConsumedMessage(
                    value=message.value(),
                    topic=message.topic(),
                    partition=message.partition(),
                    offset=message.offset(),
                )
            )

        return result

    def commit_offsets(
        self,
        messages: list[ConsumedMessage],
    ) -> None:
        """Подтвердить offsets успешно обработанного пакета."""
        self._ensure_open()

        if not messages:
            return []

        offsets = self._build_commit_offsets(
            messages,
        )

        try:
            commited_offsets = (
                self._consumer.commit(
                    offsets=offsets,
                    asynchronous=False,
                )
            )
        except KafkaException as exc:
            raise KafkaCommitError(
                "Не удалось подтвердить Kafka offsets"
            ) from exc

        if commited_offsets is None:
            raise KafkaCommitError(
                "Kafka не вернула результат commit"
            )

        failed_offsets = [
            partition for partition in commited_offsets
            if partition.error is not None
        ]
        if failed_offsets:
            raise KafkaCommitError(
                "Не удалось подтвердить offsets "
                f"для partitions: {failed_offsets}"
            )

        logger.info(
            "Kafka offsets успешно подтверждены: %s",
            [
                (
                    partition.topic,
                    partition.partition,
                    partition.offset,
                ) for partition in commited_offsets
            ],
        )

    def close(self) -> None:
        """Закрыть Kafka Consumer и покинуть consumer group."""
        if self._closed:
            return

        self._closed = True

        try:
            self._consumer.close()
        except Exception:
            logger.exception(
                "Ошибка при закрытии Kafka Consumer"
            )
        else:
            logger.info(
                "Kafka Consumer успешно закрыт"
            )

    def _ensure_open(self) -> None:
        """Проверить, что Consumer не закрыт."""
        if self._closed:
            raise KafkaConsumerClosed(
                "Kafka Consumer уже завершил работу"
            )

    @staticmethod
    def _is_partition_eof(
        message: Message,
    ) -> bool:
        """Проверить достижение конца Kafka partition."""
        error = message.error()

        return (
            error is not None
            and error.code() == KafkaError._PARTITION_EOF
        )

    @staticmethod
    def _build_commit_offsets(
        messages: list[ConsumedMessage],
    ) -> list[TopicPartition]:
        """Сформировать offsets для подтверждения пакета."""
        latest_offsets: dict[
            tuple[str, int],
            int,
        ] = {}

        for message in messages:
            key = (
                message.topic,
                message.partition,
            )

            current_offset = latest_offsets.get(key)
            if (current_offset is None or message.offset > current_offset):
                latest_offsets[key] = message.offset

        return [
            TopicPartition(
                topic,
                partition,
                offset + 1,
            )
            for (topic, partition), offset in latest_offsets.items()
        ]
