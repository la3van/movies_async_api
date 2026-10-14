"""Revoke and remove expired encrypted staff sessions."""

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from admin_auth.client import revoke
from admin_auth.models import AuthSession


class Command(BaseCommand):
    help = "Revoke expired Auth sessions and remove encrypted credentials"

    def handle(self, *args: Any, **options: Any) -> None:
        count = 0
        for record in AuthSession.objects.filter(
            expires_at__lte=timezone.now()
        ).iterator():
            revoke(record)
            count += 1
        self.stdout.write(f"Removed {count} expired sessions")
