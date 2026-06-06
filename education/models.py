from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from students.models import Student


class RiskThreshold(models.Model):
    """Seuils configurables par l'administration."""

    name = models.CharField(max_length=80, default="Configuration par défaut")
    max_absences = models.PositiveSmallIntegerField(
        default=3,
        help_text=_("Au-delà de ce nombre d'absences → contribution au risque."),
    )
    grade_drop_percent = models.PositiveSmallIntegerField(
        default=30,
        help_text=_("Baisse de notes (%) considérée comme significative."),
    )
    critical_grade_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=5.0,
        help_text=_("Note absolue en dessous de laquelle un risque est signalé"),
    )
    critical_score = models.PositiveSmallIntegerField(
        default=75,
        help_text=_("Score ≥ seuil critique → suggestion dossier psychologique."),
    )
    high_risk_score = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Seuil de risque")
        verbose_name_plural = _("Seuils de risque")

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first() or cls.objects.create()


class WeeklyEntry(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="weekly_entries"
    )
    week_start = models.DateField()
    absences = models.PositiveSmallIntegerField(default=0)
    control_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    previous_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    behavioral_incident = models.BooleanField(default=False)
    observation = models.TextField(blank=True)
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_start"]
        unique_together = [("student", "week_start")]
        verbose_name = _("Saisie hebdomadaire")
        verbose_name_plural = _("Saisies hebdomadaires")

    def __str__(self):
        return f"{self.student} — semaine du {self.week_start}"


class SubjectGrade(models.Model):
    """Notes par matière liées à une saisie hebdomadaire.

    Permet de détecter qu'un élève décroche spécifiquement en maths/sciences/etc.
    """

    class Subject(models.TextChoices):
        MATHS = "maths", _("Mathématiques")
        FRENCH = "french", _("Français")
        ARABIC = "arabic", _("Arabe")
        ENGLISH = "english", _("Anglais")
        SCIENCES = "sciences", _("Sciences")
        HISTORY = "history", _("Histoire-Géo")
        OTHER = "other", _("Autre")

    weekly_entry = models.ForeignKey(
        WeeklyEntry, on_delete=models.CASCADE, related_name="subject_grades"
    )
    subject = models.CharField(max_length=20, choices=Subject.choices)
    grade = models.DecimalField(max_digits=5, decimal_places=2)
    previous_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    class Meta:
        unique_together = [("weekly_entry", "subject")]
        verbose_name = _("Note par matière")
        verbose_name_plural = _("Notes par matière")

    def __str__(self):
        return f"{self.get_subject_display()}: {self.grade}/20"


class DailyAttendance(models.Model):
    """Présence journalière pour un suivi plus fin que la simple agrégation hebdo."""

    class Status(models.TextChoices):
        PRESENT = "present", _("Présent")
        ABSENT = "absent", _("Absent")
        LATE = "late", _("Retard")
        EXCUSED = "excused", _("Excusé")

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendances"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)
    notes = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "date")]
        ordering = ["-date"]
        verbose_name = _("Présence journalière")
        verbose_name_plural = _("Présences journalières")


class Alert(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("En attente")
        VALIDATED = "validated", _("Validée")
        RESOLVED = "resolved", _("Résolue")
        DISMISSED = "dismissed", _("Écartée")

    class Level(models.TextChoices):
        MEDIUM = "medium", _("Risque modéré")
        HIGH = "high", _("Risque élevé")
        CRITICAL = "critical", _("Risque critique")

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="alerts")
    weekly_entry = models.ForeignKey(
        WeeklyEntry, on_delete=models.CASCADE, related_name="alerts"
    )
    level = models.CharField(max_length=20, choices=Level.choices)
    risk_score = models.PositiveSmallIntegerField()
    summary = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    suggests_psych_dossier = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_alerts",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alerte {self.student} ({self.get_level_display()})"


class Intervention(models.Model):
    class Type(models.TextChoices):
        INTERVIEW = "interview", _("Entretien individuel")
        FAMILY_CONTACT = "family", _("Contact famille")
        REFERRAL = "referral", _("Orientation spécialisée")
        OTHER = "other", _("Autre")

    class Effectiveness(models.IntegerChoices):
        NOT_RATED = 0, _("Non évaluée")
        VERY_POOR = 1, _("Très peu efficace")
        POOR = 2, _("Peu efficace")
        MODERATE = 3, _("Modérée")
        GOOD = 4, _("Bonne")
        EXCELLENT = 5, _("Excellente")

    alert = models.ForeignKey(
        Alert, on_delete=models.CASCADE, related_name="interventions"
    )
    intervention_type = models.CharField(max_length=20, choices=Type.choices)
    planned_date = models.DateField()
    notes = models.TextField(blank=True)
    planned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Outcome tracking (item 10)
    effectiveness_rating = models.PositiveSmallIntegerField(
        choices=Effectiveness.choices,
        default=Effectiveness.NOT_RATED,
        help_text=_("Évalué après l'intervention"),
    )
    follow_up_notes = models.TextField(
        blank=True,
        help_text=_("Observations sur l'effet de l'intervention"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["planned_date"]

    def __str__(self):
        return f"{self.get_intervention_type_display()} — {self.planned_date}"


class TeacherRequest(models.Model):
    """Demandes d'aide envoyées par les enseignants aux conseillers"""

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente")
        IN_PROGRESS = "in_progress", _("En cours")
        RESOLVED = "resolved", _("Résolue")

    class Priority(models.TextChoices):
        LOW = "low", _("Basse")
        MEDIUM = "medium", _("Moyenne")
        HIGH = "high", _("Élevée")
        URGENT = "urgent", _("Urgente")

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="teacher_requests"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_requests",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Demande enseignant")
        verbose_name_plural = _("Demandes enseignants")

    def __str__(self):
        return f"{self.subject} - {self.student} ({self.get_status_display()})"
