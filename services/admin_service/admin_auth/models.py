"""Server-side encrypted Auth credentials bound to one Django session."""

from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuthSession(models.Model):
    objects: models.Manager["AuthSession"] = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    external_user_id = models.UUIDField()
    encrypted_tokens = models.TextField()
    expires_at = models.DateTimeField(db_index=True)
    locked_until = models.DateTimeField(default=timezone.now)
    lock_owner = models.UUIDField(null=True)
