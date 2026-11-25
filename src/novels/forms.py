"""Forms for the novels app."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Chapter, Novel


class NovelForm(forms.ModelForm):
    """Create (E2) / edit (E3) a novel.

    `author` and `is_published` are deliberately excluded: the author is set
    from `request.user` in the view, and publishing has its own action (E7).
    """

    class Meta:
        model = Novel
        fields = ('title', 'category', 'cover', 'summary', 'status')
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = _('Select a category')


class ChapterForm(forms.ModelForm):
    """Create / edit a chapter (E5), including optional scheduling (C6)."""

    class Meta:
        model = Chapter
        fields = ('title', 'content', 'scheduled_at')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 16}),
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_at'].required = False
