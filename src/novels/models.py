"""Models for the novels app (Category, Novel, Chapter)."""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Novel category (B4). Managed by admins, rarely changes.

    Translation strategy: the database stores only the English label in
    `name` (used by queries, the admin and `seed_demo`). The display text for
    the active language is resolved by `label`, which runs the English name
    through gettext (`locale/zh_Hant/LC_MESSAGES/django.po`). Templates and
    form choice lists use `label`, so no Chinese literal appears in the code
    and no localized value is ever written to the database.
    """

    name = models.CharField(_('Name'), max_length=50, unique=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']

    def __str__(self) -> str:
        return self.label

    @property
    def label(self) -> str:
        """Localized label for the current language (gettext lookup)."""
        return gettext(self.name)


class Tag(models.Model):
    """Free-form tag applied to novels (C11 extension)."""

    name = models.CharField(_('Name'), max_length=50, unique=True)

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class NovelQuerySet(models.QuerySet):
    """Reusable querysets for the browsing pages (B1, B2, B3, B4, B6)."""

    def published(self):
        return self.filter(is_published=True)


class Novel(models.Model):
    """A novel authored by a user (E1-E4, E7, F2)."""

    class Status(models.TextChoices):
        ONGOING = 'ongoing', _('Ongoing')
        COMPLETED = 'completed', _('Completed')

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='novels',
        verbose_name=_('Author'),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='novels',
        verbose_name=_('Category'),
    )
    title = models.CharField(_('Title'), max_length=200)
    cover = models.ImageField(
        _('Cover'),
        upload_to='covers/',
        blank=True,
        null=True,
    )
    summary = models.TextField(_('Summary'), blank=True)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=Status.choices,
        default=Status.ONGOING,
    )
    is_published = models.BooleanField(_('Published'), default=False)
    tags = models.ManyToManyField(
        Tag, blank=True, related_name='novels', verbose_name=_('Tags'))
    view_count = models.PositiveIntegerField(_('View count'), default=0)
    word_count = models.PositiveIntegerField(_('Word count'), default=0)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    objects = NovelQuerySet.as_manager()

    class Meta:
        verbose_name = _('Novel')
        verbose_name_plural = _('Novels')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['is_published', '-updated_at']),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        from django.urls import reverse

        return reverse('novels:novel_detail', args=[self.pk])

    def get_chapter_count(self) -> int:
        """Number of visible chapters (used on detail/list pages)."""
        return self.chapters.filter(is_active=True).count()

    def get_next_order(self) -> int:
        """Next chapter number = MAX(order) + 1, counting soft-deleted rows.

        Soft-deleted chapters keep their `order` (see `delete_chapter`), so the
        maximum must be taken over all rows, not only the active ones, to avoid
        violating the `(novel, order)` uniqueness constraint.
        """
        aggregate = self.chapters.aggregate(models.Max('order'))
        current = aggregate['order__max']
        return (current or 0) + 1


class Volume(models.Model):
    """A volume/part grouping chapters inside a novel (C4 extension)."""

    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='volumes',
        verbose_name=_('Novel'),
    )
    title = models.CharField(_('Title'), max_length=200)
    order = models.PositiveIntegerField(_('Order'), default=1)

    class Meta:
        verbose_name = _('Volume')
        verbose_name_plural = _('Volumes')
        ordering = ['order']

    def __str__(self) -> str:
        return f'{self.novel.title} - Vol.{self.order} {self.title}'


class ChapterQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def visible(self):
        """Chapters a reader may see: active, not draft, and scheduled time due."""
        return self.filter(is_active=True, is_draft=False).filter(
            models.Q(scheduled_at__isnull=True) | models.Q(scheduled_at__lte=timezone.now())
        )


class Chapter(models.Model):
    """A chapter of a novel (C1-C3, E5, E6).

    There is no draft state: a chapter becomes public as soon as it is created,
    and `published_at` simply records the creation time. Novel visibility is
    controlled exclusively by `Novel.is_published`.
    """

    novel = models.ForeignKey(
        Novel,
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name=_('Novel'),
    )
    volume = models.ForeignKey(
        Volume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapters',
        verbose_name=_('Volume'),
    )
    title = models.CharField(_('Chapter title'), max_length=200)
    content = models.TextField(_('Content'))
    order = models.PositiveIntegerField(_('Order'))
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    scheduled_at = models.DateTimeField(
        _('Scheduled at'), null=True, blank=True,
        help_text=_('If set in the future, the chapter is hidden until then.'))
    view_count = models.PositiveIntegerField(_('View count'), default=0)
    word_count = models.PositiveIntegerField(_('Word count'), default=0)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    published_at = models.DateTimeField(
        _('Published at'),
        default=timezone.now,
        help_text=_('Creation time. Chapters have no draft state.'),
    )

    objects = ChapterQuerySet.as_manager()

    class Meta:
        verbose_name = _('Chapter')
        verbose_name_plural = _('Chapters')
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=['novel', 'order'],
                name='unique_chapter_order_per_novel',
            ),
        ]
        indexes = [
            models.Index(fields=['novel', 'order']),
        ]

    def __str__(self) -> str:
        return f'{self.novel.title} - Ch.{self.order} {self.title}'

    @staticmethod
    def count_words(text) -> int:
        """Word count: Latin words by whitespace, CJK counted per character."""
        total = 0
        for token in (text or '').split():
            cjk = sum(1 for ch in token if '\u4e00' <= ch <= '\u9fff')
            latin = len([ch for ch in token if not ('\u4e00' <= ch <= '\u9fff')])
            total += cjk + (1 if latin else 0)
        return total

    def save(self, *args, **kwargs):
        self.word_count = self.count_words(self.content)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        from django.urls import reverse

        return reverse(
            'novels:chapter_read',
            args=[self.novel_id, self.order],
        )

    def get_next_chapter(self):
        """Active chapter with the next higher order, or None (C2)."""
        return (
            Chapter.objects.active()
            .filter(novel_id=self.novel_id, order__gt=self.order)
            .order_by('order')
            .first()
        )

    def get_prev_chapter(self):
        """Active chapter with the next lower order, or None (C2)."""
        return (
            Chapter.objects.active()
            .filter(novel_id=self.novel_id, order__lt=self.order)
            .order_by('-order')
            .first()
        )
