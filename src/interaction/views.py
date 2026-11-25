"""Views for the interaction app: favorites, comments, ratings."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.permissions import author_or_admin, comment_owner
from novels.models import Chapter, Novel

from .forms import CommentForm, RatingForm
from .models import Comment, Favorite, Rating


# ---------------------------------------------------------------- favorites


@login_required
@require_POST
def favorite_toggle(request, novel_pk):
    """Add or remove a favorite (D1). Single endpoint, toggle semantics (SD-1)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not novel.is_published and not author_or_admin.can_edit(novel, request.user):
        raise Http404(_('Novel not found.'))

    favorite = Favorite.objects.filter(user=request.user, novel=novel).first()
    if favorite is not None:
        favorite.delete()
        messages.success(request, _('Removed from favorites.'))
    else:
        Favorite.objects.create(user=request.user, novel=novel)
        messages.success(request, _('Added to favorites.'))
    return redirect('novels:novel_detail', pk=novel.pk)


@login_required
def my_favorites(request):
    """The user's favorite novels (D2)."""
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related('novel__author', 'novel__category')
        .order_by('-created_at')
    )
    return render(request, 'interaction/my_favorites.html', {'favorites': favorites})


# ---------------------------------------------------------------- comments


@login_required
@require_POST
def comment_create(request, novel_pk, order):
    """Post a comment or an (one-level) reply (D3, D6)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    chapter = get_object_or_404(Chapter.objects.active(), novel=novel, order=order)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.chapter = chapter
        comment.parent = form.cleaned_data.get('parent')
        comment.save()
        messages.success(request, _('Comment posted.'))
    else:
        error = form.errors.get('__all__')
        messages.error(
            request,
            error[0] if error else _('Please check your comment and try again.'),
        )
    return redirect('novels:chapter_read', novel_pk=novel.pk, order=order)


@login_required
@require_POST
def comment_delete(request, pk):
    """Soft-delete a comment (D4). Comment owner or admin; replies are hidden too."""
    comment = get_object_or_404(Comment, pk=pk)
    if not comment_owner.can_edit(comment, request.user):
        return HttpResponseForbidden(_('You are not allowed to delete this comment.'))

    comment.is_active = False
    comment.save(update_fields=['is_active'])
    # Hide the child replies as well, so no orphan replies are displayed.
    comment.replies.update(is_active=False)

    messages.success(request, _('Comment deleted.'))
    return redirect(
        'novels:chapter_read',
        novel_pk=comment.chapter.novel_id,
        order=comment.chapter.order,
    )


# ---------------------------------------------------------------- ratings


@login_required
@require_POST
def rate_novel(request, novel_pk):
    """Set or update the user's 1-5 star rating (D7)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not novel.is_published and not author_or_admin.can_edit(novel, request.user):
        raise Http404(_('Novel not found.'))

    form = RatingForm(request.POST)
    if not form.is_valid():
        messages.error(request, _('Score must be between 1 and 5.'))
        return redirect('novels:novel_detail', pk=novel.pk)

    rating, created = Rating.objects.get_or_create(
        user=request.user,
        novel=novel,
        defaults={'score': form.cleaned_data['score']},
    )
    if not created:
        rating.score = form.cleaned_data['score']
        rating.full_clean()
        rating.save(update_fields=['score', 'updated_at'])

    messages.success(request, _('Rating saved.'))
    return redirect('novels:novel_detail', pk=novel.pk)
