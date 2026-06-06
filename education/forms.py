from django import forms

from education.models import (
    Alert,
    Intervention,
    RiskThreshold,
    SubjectGrade,
    TeacherRequest,
    WeeklyEntry,
)


class WeeklyEntryForm(forms.ModelForm):
    class Meta:
        model = WeeklyEntry
        fields = [
            "student", "week_start", "absences",
            "control_grade", "previous_grade",
            "behavioral_incident", "observation",
        ]
        widgets = {
            "week_start": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "observation": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "behavioral_incident":
                field.widget.attrs.setdefault("class", "form-input")


class SubjectGradeForm(forms.ModelForm):
    class Meta:
        model = SubjectGrade
        fields = ["subject", "grade", "previous_grade"]


class CSVUploadForm(forms.Form):
    file = forms.FileField(
        label="Fichier CSV",
        help_text=(
            "Colonnes requises : internal_code, week_start, absences, "
            "control_grade, previous_grade, behavioral_incident"
        ),
    )


class InterventionForm(forms.ModelForm):
    class Meta:
        model = Intervention
        fields = ["intervention_type", "planned_date", "notes"]
        widgets = {
            "planned_date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
        }


class InterventionOutcomeForm(forms.ModelForm):
    """Évaluation post-intervention (item 10)."""

    class Meta:
        model = Intervention
        fields = ["effectiveness_rating", "follow_up_notes", "completed"]
        widgets = {
            "follow_up_notes": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "effectiveness_rating": forms.Select(attrs={"class": "form-input"}),
        }


class RiskThresholdForm(forms.ModelForm):
    class Meta:
        model = RiskThreshold
        fields = [
            "name", "max_absences", "grade_drop_percent",
            "critical_grade_threshold", "high_risk_score",
            "critical_score", "is_active",
        ]


class TeacherRequestForm(forms.ModelForm):
    class Meta:
        model = TeacherRequest
        fields = ["student", "priority", "subject", "description"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-input"}),
            "priority": forms.Select(attrs={"class": "form-input"}),
            "subject": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
        }


class AlertFilterForm(forms.Form):
    """Filtres pour la liste des alertes."""

    STATUS_CHOICES = [("", "Tous statuts")] + list(Alert.Status.choices)
    LEVEL_CHOICES = [("", "Tous niveaux")] + list(Alert.Level.choices)

    status = forms.ChoiceField(
        required=False, choices=STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    level = forms.ChoiceField(
        required=False, choices=LEVEL_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    q = forms.CharField(
        required=False, label="Recherche élève",
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
