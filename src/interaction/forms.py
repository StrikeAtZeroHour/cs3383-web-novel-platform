"""Forms for the interaction app."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from novels.models import Chapter, Novel

from .models import Comment, Discussion, DiscussionReply, Rating


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
        # Multi-level replies are allowed; `parent` just points to the target.
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


class DiscussionForm(forms.ModelForm):
    """Create a discussion post, optionally pinning a novel and chapter.

    The chapter (if given) must belong to the chosen novel so a post cannot be
    pinned to a chapter of an unrelated book.
    """

    class Meta:
        model = Discussion
        fields = ('title', 'body', 'novel', 'chapter')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('Discussion title')}),
            'body': forms.Textarea(
                attrs={'rows': 5, 'placeholder': _('Share your thoughts...')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['novel'].queryset = Novel.objects.published()
        self.fields['novel'].required = False
        self.fields['chapter'].required = False
        # Chapters are all listed; the clean() below enforces the novel match.
        self.fields['chapter'].queryset = Chapter.objects.active().select_related('novel')

    def clean(self):
        cleaned = super().clean()
        novel = cleaned.get('novel')
        chapter = cleaned.get('chapter')
        if chapter and novel and chapter.novel_id != novel.pk:
            raise ValidationError(
                _('The selected chapter does not belong to the selected novel.'))
        if chapter and not novel:
            # Pin the novel automatically from the chapter.
            cleaned['novel'] = chapter.novel
        return cleaned


class DiscussionReplyForm(forms.ModelForm):
    """Create a threaded reply to a discussion post."""

    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = DiscussionReply
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 3, 'placeholder': _('Write a reply...')}),
        }

    def __init__(self, *args, discussion=None, **kwargs):
        self.discussion = discussion
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        parent_id = cleaned.get('parent_id')
        if not parent_id:
            cleaned['parent'] = None
            return cleaned
        if self.discussion is None:
            raise ValidationError(_('The discussion no longer exists.'))
        parent = DiscussionReply.objects.filter(
            pk=parent_id, discussion=self.discussion, is_active=True).first()
        if parent is None:
            raise ValidationError(_('The reply you replied to no longer exists.'))
        cleaned['parent'] = parent
        return cleaned
