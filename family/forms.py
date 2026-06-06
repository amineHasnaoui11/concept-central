from django import forms


class RequestAccessForm(forms.Form):
    parent_email = forms.EmailField(
        label="Votre email",
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "parent@exemple.tn",
            "autofocus": True,
        }),
    )

    def clean_parent_email(self):
        return self.cleaned_data["parent_email"].strip().lower()
