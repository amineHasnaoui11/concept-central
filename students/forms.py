from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from students.models import ParentConsent, Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "internal_code", "first_name", "last_name", "birth_year",
            "level", "class_name",
            "parent_full_name", "parent_phone", "parent_email",
            "parent_preferred_language",
        ]
        widgets = {
            "internal_code": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: TN-2024-001"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "birth_year": forms.NumberInput(attrs={"class": "form-input", "min": 2006, "max": 2020}),
            "level": forms.Select(attrs={"class": "form-input"}),
            "class_name": forms.TextInput(attrs={"class": "form-input"}),
            "parent_full_name": forms.TextInput(attrs={"class": "form-input"}),
            "parent_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+216 ..."}),
            "parent_email": forms.EmailInput(attrs={"class": "form-input"}),
            "parent_preferred_language": forms.Select(attrs={"class": "form-input"}),
        }

    def clean_internal_code(self):
        code = self.cleaned_data.get("internal_code", "").strip()
        if not code:
            raise ValidationError("Le code interne est requis.")
        qs = Student.objects.filter(internal_code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Le code interne '{code}' est déjà utilisé.")
        return code

    def clean_birth_year(self):
        birth_year = self.cleaned_data.get("birth_year")
        if birth_year is None:
            raise ValidationError("L'année de naissance est requise.")
        age = date.today().year - birth_year
        if age < 10 or age > 18:
            raise ValidationError(
                f"L'âge {age} ans est hors de la plage 10–18 ans."
            )
        return birth_year


class StudentSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Recherche",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Nom, prénom ou code interne…",
        }),
    )
    level = forms.ChoiceField(
        required=False,
        choices=[("", "Tous niveaux")] + list(Student.Level.choices),
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    class_name = forms.CharField(
        required=False,
        label="Classe",
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )


class ParentConsentForm(forms.ModelForm):
    class Meta:
        model = ParentConsent
        fields = ["consent_type", "granted", "granted_by", "notes"]
        widgets = {
            "consent_type": forms.Select(attrs={"class": "form-input"}),
            "granted_by": forms.TextInput(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }
