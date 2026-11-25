"""Forms for the accounts app."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Profile


class RegisterForm(UserCreationForm):
    """Registration form (A1): username, email, password."""

    email = forms.EmailField(
        label=_('Email'),
        required=False,
        help_text=_('Optional. Never shown publicly.'),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class ProfileForm(forms.ModelForm):
    """Edit nickname / bio / avatar (A4)."""

    class Meta:
        model = Profile
        fields = ('nickname', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
