"""Views for the interaction app: favorites, comments, ratings."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.permissions import author_or_admin, comment_owner
from novels.models import Chapter, Novel

from .forms import CommentForm, DiscussionForm, DiscussionReplyForm, RatingForm
from .models import Comment, Discussion, DiscussionReply, Favorite, Rating
from .translation import TranslationError, target_language_code, translate_text


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


# ---------------------------------------------------------------- comment likes / spoilers

@login_required
@require_POST
def comment_like_toggle(request, pk):
    """Toggle a like on a comment (community extension)."""
    comment = get_object_or_404(Comment, pk=pk)
    if comment.likes.filter(pk=request.user.pk).exists():
        comment.likes.remove(request.user)
    else:
        comment.likes.add(request.user)
    return redirect(
        'novels:chapter_read',
        novel_pk=comment.chapter.novel_id,
        order=comment.chapter.order,
    )


# ---------------------------------------------------------------- translation

@require_POST
def comment_translate(request, pk):
    """Translate a comment into the reader's current UI language (like x.com).

    Returns JSON `{ok, translated, target}`. No login is required because the
    comment is already public; rate-limited only by the cache.
    """
    comment = get_object_or_404(Comment.objects.active(), pk=pk)
    target = target_language_code()
    try:
        translated = translate_text(comment.content)
    except TranslationError as exc:
        return JsonResponse(
            {'ok': False, 'error': str(exc), 'target': target}, status=502)
    return JsonResponse({'ok': True, 'translated': translated, 'target': target})


# ---------------------------------------------------------------- follow


@login_required
@require_POST
def follow_toggle(request, username):
    """Follow or unfollow an author (community extension)."""
    from django.contrib.auth.models import User
    from django.urls import reverse

    from .models import Follow

    target = get_object_or_404(User, username=username)
    if target.pk == request.user.pk:
        messages.error(request, _('You cannot follow yourself.'))
        return redirect('accounts:author_profile', username=username)
    existing = Follow.objects.filter(follower=request.user, author=target).first()
    if existing:
        existing.delete()
    else:
        Follow.objects.create(follower=request.user, author=target)
    return redirect('accounts:author_profile', username=username)


# ---------------------------------------------------------------- notifications

@login_required
def notification_list(request):
    """List the current user's notifications (C17 extension)."""
    from .models import Notification

    notifications = request.user.notifications.all()[:100]
    return render(
        request, 'interaction/notifications.html', {'notifications': notifications})


@login_required
@require_POST
def notification_read_all(request):
    """Mark all of the user's notifications read."""
    request.user.notifications.update(is_read=True)
    return redirect('interaction:notifications')


# ---------------------------------------------------------------- reports

@login_required
@require_POST
def report_create(request, novel_pk):
    """Submit a content report for a novel (F2 extension)."""
    from .models import Report

    novel = get_object_or_404(Novel, pk=novel_pk)
    reason = request.POST.get('reason', '').strip()
    if reason:
        Report.objects.create(reporter=request.user, novel=novel, reason=reason)
        messages.success(request, _('Report submitted.'))
    return redirect('novels:novel_detail', pk=novel.pk)


# ---------------------------------------------------------------- discussion board

def discussion_list(request):
    """Site-wide discussion board, optionally filtered by novel (community)."""
    discussions = (
        Discussion.objects.filter(is_active=True)
        .select_related('user__profile', 'novel', 'chapter')
        .prefetch_related('likes')
    )
    novel_id = request.GET.get('novel')
    if novel_id:
        discussions = discussions.filter(novel_id=novel_id)

    paginator = Paginator(discussions, 20)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'novels': Novel.objects.published().order_by('title'),
        'selected_novel': novel_id,
    }
    return render(request, 'interaction/discussion_list.html', context)


@login_required
def discussion_create(request):
    """Start a new discussion post; optionally pin a novel and chapter."""
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.user = request.user
            discussion.save()
            messages.success(request, _('Discussion posted.'))
            return redirect('interaction:discussion_detail', pk=discussion.pk)
    else:
        form = DiscussionForm()
    return render(
        request, 'interaction/discussion_form.html', {'form': form})


def discussion_detail(request, pk):
    """Show a discussion post and its threaded replies."""
    discussion = get_object_or_404(
        Discussion.objects.select_related('user__profile', 'novel', 'chapter'),
        pk=pk,
    )
    if not discussion.is_active and not request.user.is_staff:
        raise Http404(_('Discussion not found.'))

    replies = (
        DiscussionReply.objects.filter(
            discussion=discussion, is_active=True, parent__isnull=True)
        .select_related('user__profile')
        .prefetch_related('replies__user__profile', 'likes')
    )
    context = {
        'discussion': discussion,
        'replies': replies,
        'reply_form': DiscussionReplyForm(discussion=discussion),
    }
    return render(request, 'interaction/discussion_detail.html', context)


@login_required
@require_POST
def discussion_reply(request, pk):
    """Post a threaded reply to a discussion (any depth)."""
    discussion = get_object_or_404(Discussion, pk=pk, is_active=True)
    form = DiscussionReplyForm(request.POST, discussion=discussion)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.discussion = discussion
        reply.user = request.user
        reply.parent = form.cleaned_data.get('parent')
        reply.save()
        messages.success(request, _('Reply posted.'))
    else:
        error = form.errors.get('__all__')
        messages.error(
            request,
            error[0] if error else _('Please check your reply and try again.'),
        )
    return redirect('interaction:discussion_detail', pk=discussion.pk)


@login_required
@require_POST
def discussion_like_toggle(request, pk):
    """Toggle a like on a discussion post."""
    discussion = get_object_or_404(Discussion, pk=pk)
    if discussion.likes.filter(pk=request.user.pk).exists():
        discussion.likes.remove(request.user)
    else:
        discussion.likes.add(request.user)
    return redirect('interaction:discussion_detail', pk=discussion.pk)


@login_required
@require_POST
def discussion_reply_like_toggle(request, pk):
    """Toggle a like on a discussion reply."""
    reply = get_object_or_404(DiscussionReply, pk=pk)
    if reply.likes.filter(pk=request.user.pk).exists():
        reply.likes.remove(request.user)
    else:
        reply.likes.add(request.user)
    return redirect('interaction:discussion_detail', pk=reply.discussion_id)


@login_required
@require_POST
def discussion_delete(request, pk):
    """Soft-delete a discussion post (owner or admin); replies hidden too."""
    discussion = get_object_or_404(Discussion, pk=pk)
    is_owner = discussion.user_id == request.user.pk
    if not (is_owner or request.user.is_admin()):
        return HttpResponseForbidden(_('You are not allowed to delete this post.'))
    discussion.is_active = False
    discussion.save(update_fields=['is_active'])
    discussion.replies.update(is_active=False)
    messages.success(request, _('Discussion deleted.'))
    return redirect('interaction:discussion_list')


@login_required
@require_POST
def discussion_report(request, pk):
    """Report a discussion post (F2 extension)."""
    from .models import Report

    discussion = get_object_or_404(Discussion, pk=pk)
    reason = request.POST.get('reason', '').strip()
    if reason:
        Report.objects.create(
            reporter=request.user, discussion=discussion, reason=reason)
        messages.success(request, _('Report submitted.'))
    return redirect('interaction:discussion_detail', pk=discussion.pk)
