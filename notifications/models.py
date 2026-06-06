from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Event(models.TextChoices):
        ALERT_CREATED = "alert.created", "Alerte créée"
        SESSION_MISSED = "session.missed", "Séance manquée"
        TEACHER_REQUEST = "request.received", "Demande enseignant reçue"
        INTERVENTION_PLANNED = "intervention.planned", "Intervention planifiée"
        DOSSIER_OPENED = "dossier.opened", "Dossier ouvert"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "Application"
        EMAIL = "email", "Email"

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="notifications",
    )
    recipient_email = models.EmailField(blank=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    event = models.CharField(max_length=40, choices=Event.choices)
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_via_email_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient_user", "read_at"])]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        target = self.recipient_user or self.recipient_email or "?"
        return f"[{self.get_event_display()}] → {target}"

    @property
    def is_read(self):
        return self.read_at is not None
