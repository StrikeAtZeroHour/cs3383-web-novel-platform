"""Service layer for novel-related business operations.

See `docs/diagrams/02-class-diagram.md` (NovelService) and `04-sequence.md`
(SD-2, SD-3, SD-5). Views stay thin: they handle HTTP, permission checks and
messages; all multi-step domain logic lives here.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Chapter


class NovelService:
    """Service Layer pattern (wraps cross-model novel workflows)."""

    @staticmethod
    def publish(novel) -> None:
        """Make a novel visible (E7). Published novels need not have chapters."""
        novel.is_published = True
        novel.save(update_fields=['is_published', 'updated_at'])

    @staticmethod
    def unpublish(novel) -> None:
        """Hide a novel again (E7 / admin takedown F2). Data is kept."""
        novel.is_published = False
        novel.save(update_fields=['is_published', 'updated_at'])

    @classmethod
    @transaction.atomic
    def create_chapter(cls, novel, title, content, published_at=None) -> Chapter:
        """Append a chapter at MAX(order) + 1 and touch the novel (B1)."""
        chapter = Chapter.objects.create(
            novel=novel,
            title=title,
            content=content,
            order=novel.get_next_order(),
            published_at=published_at or timezone.now(),
        )
        cls._touch(novel)
        return chapter

    @classmethod
    def delete_chapter(cls, chapter) -> None:
        """Soft-delete a chapter; `order` is NOT renumbered (see design docs)."""
        chapter.is_active = False
        chapter.save(update_fields=['is_active'])
        cls._touch(chapter.novel)

    @classmethod
    @transaction.atomic
    def reorder_chapter(cls, chapter, new_order: int) -> None:
        """Move a chapter to `new_order` and shift the affected siblings (E6).

        `(novel, order)` is unique, so the move is done in two phases: the moved
        chapter is parked in a temporary out-of-range slot first to avoid
        transient uniqueness collisions.
        """
        novel = chapter.novel
        max_order = novel.get_next_order()
        new_order = max(1, min(new_order, max_order))

        old_order = chapter.order
        if new_order == old_order:
            return

        siblings = Chapter.objects.active().filter(novel=novel).exclude(pk=chapter.pk)

        # Park the moved chapter outside the used range.
        temp_order = max_order + 1000
        Chapter.objects.filter(pk=chapter.pk).update(order=temp_order)

        if new_order < old_order:
            # Chapters between new_order and old_order-1 move down by one.
            siblings.filter(order__gte=new_order, order__lt=old_order).update(
                order=F('order') + 1
            )
        else:
            # Chapters between old_order+1 and new_order move up by one.
            siblings.filter(order__gt=old_order, order__lte=new_order).update(
                order=F('order') - 1
            )

        Chapter.objects.filter(pk=chapter.pk).update(order=new_order)
        chapter.order = new_order
        cls._touch(novel)

    @staticmethod
    @transaction.atomic
    def delete_novel(novel) -> None:
        """Hard-delete a novel; CASCADE removes chapters, comments, favorites, ratings."""
        novel.delete()

    @staticmethod
    def _touch(novel) -> None:
        """Refresh `Novel.updated_at` so B1 "recently updated" ordering works."""
        novel.save(update_fields=['updated_at'])
