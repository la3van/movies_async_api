"""Сервисный слой приёма заданий доставки."""

from models.contract import DeliveryJob
from repositories.interfaces.jobs import JobsRepository


class IngestionService:
    """Сохранение принятого и проверенного задания доставки."""

    def __init__(self, repository: JobsRepository) -> None:
        """Принимает реализацию хранилища входящих заданий."""
        self.repository = repository

    async def ingest(self, job: DeliveryJob) -> None:
        """Сохраняет задание до подтверждения исходного сообщения."""
        await self.repository.save(job)
