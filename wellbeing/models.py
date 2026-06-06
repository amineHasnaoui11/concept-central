import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from students.models import Student


def validate_upload_extension(value):
    """Vérifie que l'extension est dans la liste autorisée."""
    ext = os.path.splitext(value.name)[1].lower()
    allowed = getattr(settings, "ALLOWED_UPLOAD_EXTENSIONS", [])
    if allowed and ext not in allowed:
        raise ValidationError(
            f"Extension {ext} non autorisée. Autorisées : {', '.join(allowed)}"
        )


def dossier_attachment_path(instance, filename):
    """Chemin sécurisé : /media/dossiers/<dossier_id>/<filename>"""
    return f"dossiers/{instance.dossier_id}/{filename}"


class PsychDossier(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", _("Ouvert")
        CLOSED = "closed", _("Clôturé")
        ARCHIVED = "archived", _("Archivé")  # conformité rétention

    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="psych_dossier"
    )
    opened_from_alert = models.ForeignKey(
        "education.Alert",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="psych_dossiers",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    summary = models.TextField(blank=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="opened_dossiers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    retention_until = models.DateField(
        null=True, blank=True,
        help_text=_("Date après laquelle le dossier doit être archivé/anonymisé"),
    )

    class Meta:
        verbose_name = _("Dossier psychologique")
        verbose_name_plural = _("Dossiers psychologiques")

    def __str__(self):
        return f"Dossier — {self.student.internal_code}"

    def save(self, *args, **kwargs):
        # Calcul auto de la date de rétention à la création
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.retention_until:
            from datetime import timedelta as _td
            years = getattr(settings, "PSYCH_DOSSIER_RETENTION_YEARS", 5)
            self.retention_until = (self.created_at + _td(days=365 * years)).date()
            super().save(update_fields=["retention_until"])


class DossierAttachment(models.Model):
    """Pièces jointes au dossier psychologique (certificats, courriers, etc.)."""

    dossier = models.ForeignKey(
        PsychDossier, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(
        upload_to=dossier_attachment_path,
        validators=[validate_upload_extension],
    )
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = _("Pièce jointe")
        verbose_name_plural = _("Pièces jointes")

    def __str__(self):
        return f"{self.file.name} ({self.dossier})"

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class FollowUpSession(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planifiée")
        COMPLETED = "completed", _("Réalisée")
        MISSED = "missed", _("Manquée")

    dossier = models.ForeignKey(
        PsychDossier, on_delete=models.CASCADE, related_name="sessions"
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLANNED
    )
    stress_level = models.PositiveSmallIntegerField(
        default=0, help_text=_("0-10 (synthétique)")
    )
    anxiety_level = models.PositiveSmallIntegerField(default=0)
    isolation_level = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Séance {self.scheduled_at:%Y-%m-%d}"


class CaseTimelineEvent(models.Model):
    dossier = models.ForeignKey(
        PsychDossier, on_delete=models.CASCADE, related_name="timeline_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    action = models.CharField(max_length=120)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Événement timeline")
        verbose_name_plural = _("Événements timeline")

    def __str__(self):
        return f"{self.action} — {self.created_at:%Y-%m-%d %H:%M}"


def add_timeline_event(dossier, actor, action, detail=""):
    return CaseTimelineEvent.objects.create(
        dossier=dossier, actor=actor, action=action, detail=detail,
    )
