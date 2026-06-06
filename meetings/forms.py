from django import forms
from django.utils import timezone

from meetings.models import Meeting


class MeetingProposalForm(forms.ModelForm):
    """Formulaire utilisé par le conseiller pour proposer un RDV."""

    class Meta:
        model = Meeting
        fields = ["scheduled_at", "duration_minutes", "topic", "counselor_notes"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-input"}
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-input", "min": 15, "max": 180, "step": 5}
            ),
            "topic": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Ex: Suivi mensuel"}
            ),
            "counselor_notes": forms.Textarea(
                attrs={"class": "form-input", "rows": 3,
                       "placeholder": "Notes internes (non visibles par l'élève)"}
            ),
        }
        labels = {
            "scheduled_at": "Date et heure",
            "duration_minutes": "Durée (minutes)",
            "topic": "Sujet visible par l'élève",
            "counselor_notes": "Notes internes",
        }

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data["scheduled_at"]
        if scheduled_at <= timezone.now():
            raise forms.ValidationError("La date doit être dans le futur.")
        return scheduled_at


class StudentResponseForm(forms.Form):
    """Formulaire utilisé par l'élève pour répondre à un RDV.

    4 actions possibles :
    - approve : accepte le RDV
    - reject : refuse définitivement
    - propose_alternate : propose une autre date (RDV reste en attente)
    """

    ACTIONS = [
        ("approve", "✓ Accepter"),
        ("reject", "✗ Refuser"),
        ("propose_alternate", "📅 Proposer une autre date"),
    ]
    action = forms.ChoiceField(
        choices=ACTIONS,
        widget=forms.RadioSelect,
        label="Votre réponse",
    )
    alternative_datetime = forms.DateTimeField(
        required=False,
        label="Date alternative proposée",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-input"}
        ),
        help_text="Requis uniquement si vous proposez une autre date.",
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-input", "rows": 3,
            "placeholder": "Message au conseiller (optionnel)",
        }),
        label="Message (optionnel)",
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        alt = cleaned.get("alternative_datetime")
        if action == "propose_alternate" and not alt:
            raise forms.ValidationError(
                "Vous devez indiquer une date alternative."
            )
        if alt and alt <= timezone.now():
            self.add_error("alternative_datetime", "La date doit être dans le futur.")
        return cleaned


class StudentCancelMeetingForm(forms.Form):
    """Formulaire pour annuler un RDV approuvé."""
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-input", "rows": 3,
            "placeholder": "Pourquoi annulez-vous ? (optionnel)",
        }),
        label="Raison de l'annulation",
    )
