import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone


def _generate_token():
    return secrets.token_urlsafe(32)


def _default_expiry():
    return timezone.now() + timedelta(minutes=15)


class ParentMagicLink(models.Model):
    """Token à usage unique pour le portail famille."""

    parent_email = models.EmailField(db_index=True)
    token = models.CharField(
        max_length=64, unique=True, default=_generate_token, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_expiry)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lien d'accès parent"
        verbose_name_plural = "Liens d'accès parent"

    def __str__(self):
        return f"Lien parent {self.parent_email} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
