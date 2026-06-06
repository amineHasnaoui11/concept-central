"""
Rendez-vous en ligne entre conseiller et élève.

Flow :
  1. Conseiller propose un RDV (status=PROPOSED)
  2. Élève approuve ou refuse
  3. Si approuvé : status=APPROVED, room_token généré
  4. À l'heure prévue (±fenêtre), les deux peuvent rejoindre via Jitsi
  5. Après l'heure : status=COMPLETED (auto ou manuel)
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Fenêtre d'accès au salon (en minutes avant et après l'heure prévue)
ACCESS_WINDOW_BEFORE_MINUTES = 10
ACCESS_WINDOW_AFTER_MINUTES = 90


def _generate_room_token():
    """Token URL-safe pour le nom de salon Jitsi (non devinable)."""
    return secrets.token_urlsafe(32)


class Meeting(models.Model):
    """Un rendez-vous proposé par un conseiller à un élève.

    L'élève doit approuver pour que le RDV soit confirmé.
    Une fois approuvé, les deux parties peuvent rejoindre le salon Jitsi
    dans une fenêtre temporelle autour de l'heure prévue.
    """

    class Status(models.TextChoices):
        PROPOSED = "proposed", _("Proposé · en attente de l'élève")
        APPROVED = "approved", _("Approuvé")
        REJECTED = "rejected", _("Refusé")
        CANCELLED = "cancelled", _("Annulé")
        COMPLETED = "completed", _("Terminé")
        MISSED = "missed", _("Manqué")

    dossier = models.ForeignKey(
        "wellbeing.PsychDossier",
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proposed_meetings",
        help_text=_("Conseiller qui a proposé le RDV"),
    )

    scheduled_at = models.DateTimeField(verbose_name=_("Date et heure prévues"))
    duration_minutes = models.PositiveSmallIntegerField(
        default=45,
        verbose_name=_("Durée prévue (min)"),
    )
    topic = models.CharField(
        max_length=200,
        verbose_name=_("Sujet du RDV"),
        help_text=_("Sera visible par l'élève"),
    )
    counselor_notes = models.TextField(
        blank=True,
        verbose_name=_("Notes du conseiller"),
        help_text=_("Notes internes — non visibles par l'élève"),
    )
    student_message = models.TextField(
        blank=True,
        verbose_name=_("Message de l'élève"),
        help_text=_("Message lors de l'approbation / refus"),
    )
    student_alternative_proposal = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Date alternative proposée par l'élève"),
        help_text=_("Si refus avec contre-proposition, l'élève suggère une autre date"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED,
    )

    # Token secret pour le salon Jitsi (généré uniquement après approbation)
    room_token = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        null=True,  # permet plusieurs vides sans collision
        help_text=_("Identifiant secret du salon Jitsi"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    counselor_joined_at = models.DateTimeField(null=True, blank=True)
    student_joined_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-scheduled_at"]
        verbose_name = _("Rendez-vous en ligne")
        verbose_name_plural = _("Rendez-vous en ligne")
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self):
        return f"RDV {self.student} — {self.scheduled_at:%d/%m/%Y %H:%M}"

    def approve(self, message=""):
        """L'élève approuve le RDV → génération du token."""
        self.status = self.Status.APPROVED
        self.responded_at = timezone.now()
        if message:
            self.student_message = message
        if not self.room_token:
            self.room_token = _generate_room_token()
        self.save()

    def reject(self, message="", alternative=None):
        self.status = self.Status.REJECTED
        self.responded_at = timezone.now()
        if message:
            self.student_message = message
        if alternative:
            self.student_alternative_proposal = alternative
        self.save()

    def propose_alternative(self, alternative_datetime, message=""):
        """L'élève propose une autre date sans rejeter outright.

        Le RDV reste PROPOSED mais avec une contre-proposition visible
        par le conseiller.
        """
        self.student_alternative_proposal = alternative_datetime
        if message:
            self.student_message = message
        self.responded_at = timezone.now()
        self.save()

    def cancel(self, by_user=None):
        """Annulation par le conseiller OU l'élève après approbation."""
        self.status = self.Status.CANCELLED
        self.save()

    @property
    def end_time(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    @property
    def access_open_at(self):
        """Date à partir de laquelle on peut rejoindre."""
        return self.scheduled_at - timedelta(minutes=ACCESS_WINDOW_BEFORE_MINUTES)

    @property
    def access_close_at(self):
        """Date après laquelle l'accès est fermé."""
        return self.scheduled_at + timedelta(minutes=ACCESS_WINDOW_AFTER_MINUTES)

    @property
    def is_joinable_now(self):
        """Le RDV est-il actuellement accessible (approuvé + dans la fenêtre) ?"""
        if self.status != self.Status.APPROVED:
            return False
        if not self.room_token:
            return False
        now = timezone.now()
        return self.access_open_at <= now <= self.access_close_at

    @property
    def is_upcoming(self):
        return (
            self.status == self.Status.APPROVED
            and self.scheduled_at > timezone.now()
        )

    @property
    def is_past(self):
        return self.access_close_at < timezone.now()

    @property
    def minutes_until_start(self):
        delta = self.scheduled_at - timezone.now()
        return int(delta.total_seconds() / 60)

    def can_be_accessed_by(self, user):
        """Détermine si un utilisateur peut accéder à ce RDV.

        Seuls le conseiller propriétaire et l'élève concerné peuvent.
        """
        if not user.is_authenticated:
            return False
        if user == self.counselor:
            return True
        if hasattr(user, "student_profile") and user.student_profile == self.student:
            return True
        return False
