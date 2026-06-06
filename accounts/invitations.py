"""
Système d'invitation pour la création autonome des comptes élèves.

Workflow :
  1. Conseiller/admin génère une invitation pour un élève → code affiché 1×
  2. Conseiller communique le code à l'élève (papier, en main propre, etc.)
  3. Élève se rend sur /inscription/, fournit son code interne + le code d'invitation
  4. L'élève choisit son propre username (ou utilise celui suggéré) + mot de passe
  5. Le compte est créé, lié au Student, l'invitation est marquée comme utilisée
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_invitation_code():
    """Format lisible humain : INV-XXXX-XXXX-XXXX (12 chars hex en blocs)."""
    # Caractères sans ambiguïté (pas de O/0, I/1, etc.)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    blocks = []
    for _ in range(3):
        blocks.append("".join(secrets.choice(alphabet) for _ in range(4)))
    return "INV-" + "-".join(blocks)


def _default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class StudentInvitation(models.Model):
    """Code d'invitation à usage unique pour qu'un élève crée son compte."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    code = models.CharField(
        max_length=24,
        unique=True,
        default=_generate_invitation_code,
        editable=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_invitation_expiry)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_invitation",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Invitation élève")
        verbose_name_plural = _("Invitations élèves")
        indexes = [
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        status = "✓ utilisé" if self.used_at else ("⏰ expiré" if self.is_expired else "⏳ valide")
        return f"{self.code} → {self.student} ({status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def mark_used(self, user):
        self.used_at = timezone.now()
        self.used_by_user = user
        self.save(update_fields=["used_at", "used_by_user"])
