"""Revoke the corresponding Auth session when Django logs out."""

from typing import Any
from uuid import UUID

from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.http import HttpRequest

from admin_auth.client import revoke
from admin_auth.models import AuthSession


@receiver(user_logged_out)
def revoke_auth_session(
    sender: Any, request: HttpRequest | None, **kwargs: Any
) -> None:
    if request is None:
        return
    try:
        identity = UUID(str(request.session.get("auth_session_id", "")))
    except ValueError:
        return
    record = AuthSession.objects.filter(pk=identity).first()
    if record is not None:
        revoke(record)
