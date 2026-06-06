from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class EventType(models.TextChoices):
        CSV_IMPORT_FAILED = "csv_import_failed", "Échec import CSV"
        ACCESS_DENIED = "access_denied", "Accès refusé"
        ALERT_CREATED = "alert_created", "Alerte créée"
        INTERVENTION_PLANNED = "intervention_planned", "Intervention planifiée"
        DOSSIER_OPENED = "dossier_opened", "Dossier psychologique ouvert"
        SESSION_MISSED = "session_missed", "Séance manquée"
        LLM_RECOMMENDATION = "llm_recommendation", "Recommandation LLM générée"

    event_type = models.CharField(max_length=40, choices=EventType.choices)
    message = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.created_at:%Y-%m-%d %H:%M}"


def log_event(event_type, message, user=None, student=None, **metadata):
    return AuditLog.objects.create(
        event_type=event_type,
        message=message,
        user=user,
        student=student,
        metadata=metadata,
    )
