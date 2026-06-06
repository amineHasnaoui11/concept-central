"""Modèles de conformité (RGPD-style).

Trace les demandes d'accès aux données par les parents.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DataAccessRequest(models.Model):
    """Trace les demandes de droit d'accès aux données."""

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente")
        PROCESSED = "processed", _("Traitée")
        REJECTED = "rejected", _("Rejetée")

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="data_access_requests",
    )
    requester_email = models.EmailField()
    request_type = models.CharField(
        max_length=20,
        choices=[
            ("access", _("Droit d'accès")),
            ("rectification", _("Rectification")),
            ("erasure", _("Effacement")),
            ("portability", _("Portabilité")),
        ],
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    response_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Demande d'accès aux données")
        verbose_name_plural = _("Demandes d'accès aux données")

    def __str__(self):
        return f"{self.get_request_type_display()} — {self.student}"
