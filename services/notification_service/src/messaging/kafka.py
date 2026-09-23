"""Асинхронная граница над тем же librdkafka, что и в events_service."""

import asyncio
import time
from dataclasses import dataclass

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
)
from confluent_kafka import (
    TopicPartition as KafkaPartition,
)
from core.config import Settings


@dataclass(frozen=True)
class TopicPartition:
    """Координаты партиции для точного подтверждения offset."""

    topic: str
    partition: int


@dataclass(frozen=True)
class ConsumerRecord:
    """Сообщение Kafka с исходными байтами и координатами."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None


class Publisher:
    """Публикатор Kafka, ожидающий подтверждения брокера."""

    def __init__(self, settings: Settings) -> None:
        """Создаёт producer с идемпотентностью и ожиданием всех ISR."""
        self.timeout = settings.kafka_timeout_seconds
        self.topics = list({settings.jobs_topic, settings.dlq_topic})
        self.last_probe = 0.0
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "enable.idempotence": True,
                "acks": "all",
                "delivery.timeout.ms": int(self.timeout * 1000),
                "request.timeout.ms": min(10000, int(self.timeout * 1000)),
                "message.max.bytes": 2097152,
                "allow.auto.create.topics": False,
            }
        )

    async def start(self) -> None:
        """Проверяет доступность Kafka и ожидаемых топиков."""
        await self.probe()

    async def close(self) -> None:
        """Дожидается завершения накопленных публикаций Kafka."""
        await asyncio.to_thread(self.producer.flush, self.timeout)

    async def probe(self) -> None:
        """Проверяет наличие топиков и доступность лидеров партиций."""
        if time.monotonic() - self.last_probe < 5:
            return
        metadata = await asyncio.to_thread(
            self.producer.list_topics,
            timeout=self.timeout,
        )
        for name in self.topics:
            topic = metadata.topics.get(name)
            if (
                topic is None
                or topic.error
                or not topic.partitions
                or any(
                    p.error or p.leader < 0 for p in topic.partitions.values()
                )
            ):
                raise RuntimeError("Kafka topic or leader unavailable")
        self.last_probe = time.monotonic()

    def _publish(self, topic: str, key: bytes, value: bytes) -> None:
        """Публикует байты и ожидает успешного delivery callback."""
        errors: list[KafkaError] = []
        acknowledged = False

        def delivered(error: KafkaError | None, message: Message) -> None:
            """Запоминает подтверждение брокера или ошибку доставки."""
            nonlocal acknowledged
            acknowledged = True
            if error is not None:
                errors.append(error)

        self.producer.produce(
            topic, key=key, value=value, on_delivery=delivered
        )
        remaining = self.producer.flush(self.timeout)
        if errors:
            raise KafkaException(errors[0])
        if remaining or not acknowledged:
            raise TimeoutError("Kafka delivery acknowledgement timed out")

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        """Выполняет блокирующую публикацию вне цикла asyncio."""
        await asyncio.to_thread(self._publish, topic, key, value)


class JobConsumer:
    """Потребитель Kafka с явным управлением подтверждениями."""

    def __init__(self, settings: Settings) -> None:
        """Создаёт consumer без автоматического подтверждения offset."""
        self.topic = settings.jobs_topic
        self.consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.consumer_group,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "earliest",
                "max.poll.interval.ms": 300000,
                "socket.timeout.ms": int(
                    settings.kafka_timeout_seconds * 1000
                ),
                "allow.auto.create.topics": False,
            }
        )

    async def start(self) -> None:
        """Подписывает consumer на настроенный топик."""
        await asyncio.to_thread(self.consumer.subscribe, [self.topic])

    async def poll(self) -> ConsumerRecord | None:
        """Возвращает одно сообщение или None при отсутствии данных."""
        message = await asyncio.to_thread(self.consumer.poll, 1.0)
        if message is None:
            return None
        error = message.error()
        if error is not None:
            raise KafkaException(error)
        topic, partition, offset = (
            message.topic(),
            message.partition(),
            message.offset(),
        )
        if topic is None or partition is None or offset is None:
            raise RuntimeError("Kafka returned a record without coordinates")
        return ConsumerRecord(
            topic=topic,
            partition=partition,
            offset=offset,
            key=message.key(),
            value=message.value(),
        )

    async def commit(self, offsets: dict[TopicPartition, int]) -> None:
        """Синхронно подтверждает заданные offsets и проверяет ошибки."""
        partitions = [
            KafkaPartition(tp.topic, tp.partition, offset)
            for tp, offset in offsets.items()
        ]
        result = await asyncio.to_thread(
            self.consumer.commit,
            offsets=partitions,
            asynchronous=False,
        )
        for partition in result or []:
            if partition.error is not None:
                raise KafkaException(partition.error)

    async def stop(self) -> None:
        """Закрывает consumer и освобождает его ресурсы."""
        await asyncio.to_thread(self.consumer.close)
