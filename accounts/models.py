from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    OPERATOR = "operator", _("Opérateur (Enseignant)")
    SUPERVISOR = "supervisor", _("Superviseur (Conseiller / Psychologue)")
    ADMIN = "admin", _("Admin (Direction)")
    STUDENT = "student", _("Élève")


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
    )

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")

    def is_operator(self):
        return self.role == Role.OPERATOR

    def is_supervisor(self):
        return self.role == Role.SUPERVISOR

    def is_admin_user(self):
        return self.role == Role.ADMIN

    def is_student(self):
        return self.role == Role.STUDENT


# Expose StudentInvitation pour les imports
from accounts.invitations import StudentInvitation  # noqa: E402,F401
