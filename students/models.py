from django.conf import settings
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Student(models.Model):
    class Level(models.TextChoices):
        COLLEGE = "college", _("Collège")
        LYCEE = "lycee", _("Lycée")

    class Language(models.TextChoices):
        FRENCH = "fr", _("Français")
        ARABIC = "ar", _("العربية")

    internal_code = models.CharField(
        max_length=32,
        unique=True,
        help_text=_("Identifiant interne (jamais envoyé au LLM en clair avec le nom)."),
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    birth_year = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=10, choices=Level.choices)
    class_name = models.CharField(max_length=40, verbose_name=_("Classe"))
    created_at = models.DateTimeField(auto_now_add=True)

    # Contact famille
    parent_full_name = models.CharField(
        max_length=160, blank=True, verbose_name=_("Nom du parent / tuteur")
    )
    parent_phone = models.CharField(
        max_length=32, blank=True, verbose_name=_("Téléphone parent")
    )
    parent_email = models.EmailField(
        blank=True,
        verbose_name=_("Email parent"),
        help_text=_("Utilisé pour le lien d'accès au portail famille."),
    )
    parent_preferred_language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.FRENCH,
        verbose_name=_("Langue préférée"),
    )

    # Lien optionnel vers un compte User (rôle STUDENT)
    # Permet à l'élève de se connecter et participer à des RDV en ligne
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="student_profile",
        help_text=_("Compte de connexion de l'élève (créé par le conseiller)."),
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = _("Élève")
        verbose_name_plural = _("Élèves")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.class_name})"

    @property
    def has_family_contact(self):
        return bool(self.parent_email or self.parent_phone)

    @property
    def age_approx(self):
        from datetime import date

        return date.today().year - self.birth_year

    def anonymized_profile(self):
        """Profil pour le LLM — sans nom réel."""
        return {
            "pseudonym": f"ELEVE-{self.internal_code}",
            "age_range": f"{self.age_approx} ans",
            "level": self.get_level_display(),
            "class_group": self.class_name,
        }


class ParentConsent(models.Model):
    """Trace le consentement parental pour le suivi des données.

    Critique pour la conformité RGPD / loi tunisienne 2004-63.
    """

    class ConsentType(models.TextChoices):
        DATA_PROCESSING = "data", _("Traitement des données scolaires")
        PSYCH_FOLLOWUP = "psych", _("Suivi psychologique")
        FAMILY_PORTAL = "portal", _("Accès portail famille")
        LLM_PROCESSING = "llm", _("Analyse IA (anonymisée)")

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="consents"
    )
    consent_type = models.CharField(max_length=10, choices=ConsentType.choices)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    granted_by = models.CharField(
        max_length=160, blank=True,
        help_text=_("Nom du parent / tuteur qui a accordé le consentement"),
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "consent_type")]
        verbose_name = _("Consentement parental")
        verbose_name_plural = _("Consentements parentaux")

    def __str__(self):
        status = "✓" if self.granted else "✗"
        return f"{status} {self.get_consent_type_display()} — {self.student}"

    @property
    def is_active(self):
        return self.granted and not self.revoked_at
