from django import forms

from wellbeing.models import DossierAttachment, FollowUpSession, PsychDossier


class DossierForm(forms.ModelForm):
    class Meta:
        model = PsychDossier
        fields = ["summary"]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4, "class": "form-input"}),
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = FollowUpSession
        fields = ["scheduled_at", "stress_level", "anxiety_level", "isolation_level", "notes"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-input"}
            ),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ("stress_level", "anxiety_level", "isolation_level"):
            self.fields[f].widget.attrs.update({"class": "form-input", "min": 0, "max": 10})


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DossierAttachment
        fields = ["file", "description"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-input"}),
        }
