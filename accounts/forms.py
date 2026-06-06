from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Identifiant"),
        widget=forms.TextInput(attrs={"class": "form-input", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
    )


class StudentSignupForm(forms.Form):
    """Formulaire d'inscription d'un élève à partir d'un code d'invitation."""

    invitation_code = forms.CharField(
        label=_("Code d'invitation"),
        max_length=24,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "INV-XXXX-XXXX-XXXX",
            "autocomplete": "off",
            "autocapitalize": "characters",
        }),
        help_text=_("Code fourni par votre conseiller (format INV-XXXX-XXXX-XXXX)."),
    )
    internal_code = forms.CharField(
        label=_("Votre code élève"),
        max_length=32,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Ex: TN-2024-001",
            "autocomplete": "off",
        }),
        help_text=_("Code interne fourni par l'école (sur votre carte ou par votre conseiller)."),
    )
    username = forms.CharField(
        label=_("Choisir un identifiant de connexion"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "autocomplete": "username",
            "placeholder": "Ex: youssef.benali",
        }),
        help_text=_("Lettres, chiffres et _ uniquement."),
    )
    password1 = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "autocomplete": "new-password",
        }),
        help_text=_("Au moins 8 caractères, pas trop simple."),
    )
    password2 = forms.CharField(
        label=_("Confirmer le mot de passe"),
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "autocomplete": "new-password",
        }),
    )

    def clean_invitation_code(self):
        code = self.cleaned_data["invitation_code"].strip().upper()
        if not code.startswith("INV-"):
            raise ValidationError(_("Format invalide. Le code commence par INV-"))
        return code

    def clean_internal_code(self):
        return self.cleaned_data["internal_code"].strip().upper()

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise ValidationError(_("Caractères invalides dans l'identifiant."))
        if len(username) < 3:
            raise ValidationError(_("Identifiant trop court (3 caractères min)."))
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError(_("Les deux mots de passe ne correspondent pas."))
        if p1:
            try:
                validate_password(p1)
            except ValidationError as e:
                self.add_error("password1", e)
        return cleaned
