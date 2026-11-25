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


class ReadingProgress(models.Model):
    """Per-user, per-novel reading position (C5). One row per (user, novel).

    Stores which chapter the user last read so the reader page can offer
    "continue reading". The latest chapter wins on update.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_progress',
        verbose_name=_('User'),
    )
    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='reading_progress',
        verbose_name=_('Novel'),
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='reading_progress',
        verbose_name=_('Chapter'),
    )
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Reading progress')
        verbose_name_plural = _('Reading progress')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'novel'],
                name='unique_progress_per_user_novel',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user} @ {self.novel} -> Ch.{self.chapter.order}'


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
    is_spoiler = models.BooleanField(_('Spoiler'), default=False)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='liked_comments',
        verbose_name=_('Likes'),
    )
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


class Notification(models.Model):
    """An in-app notification for a user (C17 extension)."""

    class Kind(models.TextChoices):
        REPLY = 'reply', _('Reply')
        NEW_CHAPTER = 'new_chapter', _('New chapter')

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient'),
    )
    kind = models.CharField(_('Kind'), max_length=20, choices=Kind.choices)
    message = models.CharField(_('Message'), max_length=255)
    url = models.CharField(_('URL'), max_length=255, blank=True)
    is_read = models.BooleanField(_('Read'), default=False)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.recipient}: {self.message}'


class Follow(models.Model):
    """A user follows an author (community extension)."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Follow')
        verbose_name_plural = _('Follows')
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'author'],
                name='unique_follow_per_pair',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.follower} follows {self.author}'


class Report(models.Model):
    """A user-submitted content report (F2 extension / moderation queue)."""

    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        RESOLVED = 'resolved', _('Resolved')
        REJECTED = 'rejected', _('Rejected')

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
    )
    reason = models.TextField(_('Reason'))
    status = models.CharField(
        _('Status'), max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Report #{self.pk} ({self.status})'


class OutlineItem(models.Model):
    """A planning entry in an author's writing workspace (lightweight)."""

    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='outline',
        verbose_name=_('Novel'),
    )
    title = models.CharField(_('Title'), max_length=200)
    body = models.TextField(_('Body'), blank=True)
    order = models.PositiveIntegerField(_('Order'), default=1)

    class Meta:
        verbose_name = _('Outline item')
        verbose_name_plural = _('Outline items')
        ordering = ['order']

    def __str__(self) -> str:
        return self.title
