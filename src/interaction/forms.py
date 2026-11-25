"""Forms for the interaction app."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Comment, Rating


class CommentForm(forms.ModelForm):
    """Create a comment or a reply (D3, D6).

    Replies are limited to one level: the parent comment must itself be a
    top-level comment. The rule lives here so it can be unit tested (G3).
    """

    parent_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput,
    )

    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 3, 'placeholder': _('Write a comment...')}
            ),
        }

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if not content:
            raise ValidationError(_('Comment cannot be empty.'))
        return content

    def clean(self):
        cleaned = super().clean()
        parent_id = cleaned.get('parent_id')
        if not parent_id:
            cleaned['parent'] = None
            return cleaned

        parent = Comment.objects.active().filter(pk=parent_id).first()
        if parent is None:
            raise ValidationError(_('The comment you replied to no longer exists.'))
        if parent.parent_id is not None:
            raise ValidationError(_('Only one level of reply is allowed.'))
        cleaned['parent'] = parent
        return cleaned


class RatingForm(forms.Form):
    """1-5 star rating (D7)."""

    score = forms.IntegerField(min_value=1, max_value=5, label=_('Score'))


class RatingModelForm(forms.ModelForm):
    """Optional ModelForm around Rating (re-uses `Rating.clean`)."""

    class Meta:
        model = Rating
        fields = ('score',)
