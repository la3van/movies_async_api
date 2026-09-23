"""Получение адресата из Auth, персонализация и SMTP-отправка."""

import asyncio
import random
from email.message import EmailMessage
from uuid import UUID

import aiosmtplib
import httpx
from core.config import Settings
from models.contract import DeliveryJob
from pydantic import BaseModel, EmailStr, StrictBool

from services.rendering import render


class PermanentFailure(Exception):
    """Ошибка доставки, для которой повтор не требуется."""

    pass


class TransientFailure(Exception):
    """Временная ошибка зависимости, допускающая повтор."""

    pass


class Recipient(BaseModel):
    """Данные активного получателя, загружаемые только перед отправкой."""

    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    is_active: StrictBool


class DeliveryService:
    """Персонализация письма и отправка через настроенный SMTP."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        """Сохраняет настройки SMTP и HTTP-клиент Auth."""
        self.settings = settings
        self.client = client

    async def send(self, job: DeliveryJob) -> None:
        """Выполняет попытку отправки с общим дедлайном меньше срока аренды."""
        await asyncio.wait_for(self._send(job), timeout=60)

    async def _send(self, job: DeliveryJob) -> None:
        """Получает адресата, формирует письмо и классифицирует ошибки SMTP."""
        response = await self.client.get(
            "internal/notifications/users/" + str(job.user_id),
            headers={
                "X-Service-Token": (
                    self.settings.internal_token.get_secret_value()
                )
            },
        )
        if response.status_code in (404, 410):
            raise PermanentFailure("recipient_unavailable")
        if response.status_code != 200:
            raise TransientFailure("auth_unavailable")
        try:
            recipient = Recipient.model_validate(response.json())
        except ValueError as exc:
            raise TransientFailure("invalid_auth_response") from exc
        if not recipient.is_active or recipient.id != job.user_id:
            raise PermanentFailure("recipient_unavailable")
        context = {
            **job.context,
            "first_name": recipient.first_name or "",
            "last_name": recipient.last_name or "",
        }
        try:
            subject = render(job.template.subject, context)
            body = render(
                job.template.body, context, job.template.body_format == "html"
            )
            if "\r" in subject or "\n" in subject:
                raise ValueError("Invalid subject")
            message = EmailMessage()
            message["From"] = self.settings.smtp_sender
            message["To"] = str(recipient.email)
            message["Subject"] = subject
            message["Message-ID"] = f"<{job.delivery_id}@notifications.local>"
            message.set_content(
                body,
                subtype="html"
                if job.template.body_format == "html"
                else "plain",
            )
        except ValueError as exc:
            raise PermanentFailure("invalid_template") from exc
        mode = self.settings.smtp_mode
        if mode not in {"plain", "starttls", "tls"}:
            raise PermanentFailure("invalid_smtp_config")
        try:
            errors, _ = await aiosmtplib.send(
                message,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_username or None,
                password=self.settings.smtp_password.get_secret_value()
                or None,
                use_tls=mode == "tls",
                start_tls=mode == "starttls",
                timeout=self.settings.smtp_timeout,
            )
            if errors:
                raise PermanentFailure("recipient_rejected")
        except aiosmtplib.errors.SMTPRecipientsRefused as exc:
            if all(item.code >= 500 for item in exc.recipients):
                raise PermanentFailure("recipient_rejected") from exc
            raise TransientFailure("smtp_temporary_failure") from exc
        except aiosmtplib.errors.SMTPResponseException as exc:
            if exc.code >= 500:
                raise PermanentFailure("smtp_rejected") from exc
            raise TransientFailure("smtp_temporary_failure") from exc

    def delay(self, attempt: int) -> float:
        """Рассчитывает ограниченную экспоненциальную задержку с jitter."""
        base = self.settings.retry_base_seconds * (2.0 ** (attempt - 1))
        return float(
            min(
                self.settings.retry_max_seconds,
                base * random.uniform(0.8, 1.2),
            )
        )
