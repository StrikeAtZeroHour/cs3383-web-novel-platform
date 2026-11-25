"""Models for the interaction app (Favorite, Comment, Rating)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from novels.models import Chapter, Novel


class Favorite(models.Model):
    """A user saved a novel (D1, D2). One-off action, no `updated_at`."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_('User'),
    )
    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_('Novel'),
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Favorite')
        verbose_name_plural = _('Favorites')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'novel'],
                name='unique_favorite_per_user_novel',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.user} -> {self.novel}'


class CommentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def top_level(self):
        """Top-level comments only (replies are fetched via `get_replies`)."""
        return self.filter(parent__isnull=True)


class Comment(models.Model):
    """A comment on a chapter (D3, D4, D6). Replies are one level deep only.

    Comments cannot be edited, so there is no `updated_at`; deletion is a soft
    delete (`is_active=False`).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('User'),
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Chapter'),
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Reply to'),
    )
    content = models.TextField(_('Content'))
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['chapter', 'created_at']),
            models.Index(fields=['parent']),
        ]

    def __str__(self) -> str:
        return f'{self.user} on {self.chapter}: {self.content[:30]}'

    def get_replies(self):
        """Active replies to this comment (D6)."""
        return Comment.objects.active().filter(parent=self)


class Rating(models.Model):
    """A 1-5 star rating of a novel by a user (D7). Editable -> has `updated_at`."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('User'),
    )
    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('Novel'),
    )
    score = models.PositiveSmallIntegerField(
        _('Score'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Rating')
        verbose_name_plural = _('Ratings')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'novel'],
                name='unique_rating_per_user_novel',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user} rated {self.novel}: {self.score}'

    def clean(self):
        """Enforce 1-5 at the application layer too (G3)."""
        super().clean()
        if self.score is not None and not 1 <= self.score <= 5:
            raise ValidationError({'score': _('Score must be between 1 and 5.')})
