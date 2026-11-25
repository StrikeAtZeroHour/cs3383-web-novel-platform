"""Views for the novels app: browsing (B1-B7) and authoring (E1-E7).

Thin views: HTTP handling, permission checks and messages only. Multi-step
workflows delegate to `NovelService`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.permissions import author_or_admin
from interaction.forms import CommentForm
from interaction.models import Comment, Notification, Rating, ReadingProgress

from .forms import ChapterForm, NovelForm
from .models import Category, Chapter, Novel, Tag, Volume
from .services import NovelService

PAGE_SIZE = 12

# ---------------------------------------------------------------- browsing


def home(request):
    """Landing page: recently updated + most favorited novels (B1)."""
    base = Novel.objects.published().select_related('author', 'category')
    context = {
        'recent': base.order_by('-updated_at')[:8],
        'popular': base.annotate(favorite_count=Count('favorites'))
        .order_by('-favorite_count', '-updated_at')[:8],
        'categories': Category.objects.all(),
    }
    return render(request, 'novels/home.html', context)


def novel_list(request):
    """Browse / search / filter / sort (B2, B3, B4, B6)."""
    novels = (
        Novel.objects.published()
        .select_related('author', 'category')
        .annotate(favorite_count=Count('favorites', distinct=True))
    )

    query = request.GET.get('q', '').strip()
    if query:
        novels = novels.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(author__username__icontains=query)
        )

    category_id = request.GET.get('category', '').strip()
    if category_id.isdigit():
        novels = novels.filter(category_id=int(category_id))

    tag = request.GET.get('tag', '').strip()
    if tag:
        novels = novels.filter(tags__name=tag)

    status = request.GET.get('status', '').strip()
    if status in dict(Novel.Status.choices):
        novels = novels.filter(status=status)

    min_words = request.GET.get('min_words', '').strip()
    if min_words.isdigit():
        novels = novels.filter(word_count__gte=int(min_words))

    sort = request.GET.get('sort', 'updated')
    sort_map = {
        'updated': ('-updated_at',),
        'newest': ('-created_at',),
        'popular': ('-favorite_count', '-updated_at'),
        'title': ('title',),
        'views': ('-view_count',),
        'rating': ('-avg_rating', '-updated_at'),
    }
    novels = novels.annotate(avg_rating=Avg('ratings__score'))
    novels = novels.order_by(*sort_map.get(sort, sort_map['updated']))

    paginator = Paginator(novels, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'query': query,
        'selected_category': category_id,
        'selected_tag': tag,
        'selected_status': status,
        'min_words': min_words,
        'sort': sort,
    }
    return render(request, 'novels/novel_list.html', context)


def novel_detail(request, pk):
    """Novel detail: info, chapters, comments, rating (B5)."""
    novel = get_object_or_404(
        Novel.objects.select_related('author', 'category'), pk=pk
    )
    is_author_or_admin = author_or_admin.can_edit(novel, request.user)

    # Unpublished novels are only visible to their author / admins.
    if not novel.is_published and not is_author_or_admin:
        raise Http404(_('Novel not found.'))

    # Count a view for the public page (authors/admins previewing excluded).
    if novel.is_published and not is_author_or_admin:
        Novel.objects.filter(pk=novel.pk).update(view_count=F('view_count') + 1)

    chapters = novel.chapters.filter(is_active=True, is_draft=False).order_by('order')
    stats = novel.ratings.aggregate(avg=Avg('score'), total=Count('pk'))
    user_rating = None
    is_favorited = False
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(user=request.user, novel=novel).first()
        is_favorited = novel.favorites.filter(user=request.user).exists()

    context = {
        'novel': novel,
        'chapters': chapters,
        'is_author_or_admin': is_author_or_admin,
        'favorite_count': novel.favorites.count(),
        'comment_count': Comment.objects.active().filter(chapter__novel=novel).count(),
        'avg_score': stats['avg'],
        'rating_count': stats['total'],
        'user_rating': user_rating,
        'is_favorited': is_favorited,
        'progress': (
            ReadingProgress.objects.filter(user=request.user, novel=novel)
            .select_related('chapter')
            .first()
            if request.user.is_authenticated
            else None
        ),
    }
    return render(request, 'novels/novel_detail.html', context)


def chapter_read(request, novel_pk, order):
    """Read a chapter (C1, C2, C3, C4). Guests are allowed."""
    novel = get_object_or_404(Novel.objects.select_related('author'), pk=novel_pk)
    is_author_or_admin = author_or_admin.can_edit(novel, request.user)
    if not novel.is_published and not is_author_or_admin:
        raise Http404(_('Novel not found.'))

    chapter = get_object_or_404(
        Chapter.objects.visible(), novel=novel, order=order
    )

    if novel.is_published and not is_author_or_admin:
        Chapter.objects.filter(pk=chapter.pk).update(
            view_count=F('view_count') + 1)

    if request.user.is_authenticated:
        # C5: remember the last chapter read for this user/novel.
        ReadingProgress.objects.update_or_create(
            user=request.user,
            novel=novel,
            defaults={'chapter': chapter},
        )

    comments = (
        Comment.objects.active()
        .top_level()
        .filter(chapter=chapter)
        .select_related('user')
        .prefetch_related('replies__user')
    )
    paginator = Paginator(comments, 20)  # D5: comment pagination
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'novel': novel,
        'chapter': chapter,
        'prev_chapter': chapter.get_prev_chapter(),
        'next_chapter': chapter.get_next_chapter(),
        'page_obj': page,
        'comment_form': CommentForm(),
    }
    return render(request, 'novels/chapter_read.html', context)


# ---------------------------------------------------------------- authoring: novels


@login_required
def my_novels(request):
    """The author's own novels, published and unpublished (E1)."""
    novels = (
        Novel.objects.filter(author=request.user)
        .select_related('category')
        .annotate(
            chapter_count=Count('chapters', filter=Q(chapters__is_active=True)),
            favorite_count=Count('favorites', distinct=True),
            comment_count=Count('chapters__comments', distinct=True),
        )
    )
    paginator = Paginator(novels, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'novels/my_novels.html', {'page_obj': page})


@login_required
def novel_create(request):
    """Create a new novel via ModelForm (E2). Author is set by the server."""
    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES)
        if form.is_valid():
            novel = form.save(commit=False)
            novel.author = request.user
            novel.is_published = False
            novel.save()
            messages.success(request, _('Novel created. Publish it when ready.'))
            return redirect('novels:my_novels')
    else:
        form = NovelForm()

    return render(request, 'novels/novel_form.html', {'form': form, 'is_new': True})


@login_required
def novel_edit(request, pk):
    """Edit a novel's metadata (E3). Author or admin only."""
    novel = get_object_or_404(Novel, pk=pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))

    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES, instance=novel)
        if form.is_valid():
            form.save()
            messages.success(request, _('Novel updated.'))
            return redirect('novels:my_novels')
    else:
        form = NovelForm(instance=novel)

    return render(
        request, 'novels/novel_form.html', {'form': form, 'novel': novel, 'is_new': False}
    )


@login_required
@require_POST
def novel_delete(request, pk):
    """Hard-delete a novel (E4). Author or admin only."""
    novel = get_object_or_404(Novel, pk=pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to delete this novel.'))

    NovelService.delete_novel(novel)
    messages.success(request, _('Novel deleted.'))
    return redirect('novels:my_novels')


@login_required
@require_POST
def novel_publish(request, pk):
    """Publish a novel (E7). No chapter count requirement."""
    novel = get_object_or_404(Novel, pk=pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to publish this novel.'))

    if novel.is_published:
        NovelService.unpublish(novel)
        messages.success(request, _('Novel unpublished.'))
    else:
        NovelService.publish(novel)
        messages.success(request, _('Novel published.'))
    return redirect('novels:my_novels')


# ---------------------------------------------------------------- authoring: chapters


@login_required
def chapter_create(request, novel_pk):
    """Add a chapter (E5). Permission check happens before any write (SD-3)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))

    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = NovelService.create_chapter(
                novel,
                title=form.cleaned_data['title'],
                content=form.cleaned_data['content'],
            )
            chapter.scheduled_at = form.cleaned_data.get('scheduled_at')
            chapter.save(update_fields=['scheduled_at'])
            messages.success(request, _('Chapter added.'))
            return redirect('novels:novel_detail', pk=novel.pk)
    else:
        form = ChapterForm()

    return render(request, 'novels/chapter_form.html', {'form': form, 'novel': novel})


@login_required
def chapter_edit(request, novel_pk, pk):
    """Edit chapter text (E5)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))

    chapter = get_object_or_404(Chapter, pk=pk, novel=novel)
    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            NovelService._touch(novel)
            messages.success(request, _('Chapter updated.'))
            return redirect('novels:novel_detail', pk=novel.pk)
    else:
        form = ChapterForm(instance=chapter)

    return render(
        request,
        'novels/chapter_form.html',
        {'form': form, 'novel': novel, 'chapter': chapter},
    )


@login_required
@require_POST
def chapter_delete(request, novel_pk, pk):
    """Soft-delete a chapter (E5). `order` is not renumbered."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))

    chapter = get_object_or_404(Chapter, pk=pk, novel=novel)
    NovelService.delete_chapter(chapter)
    messages.success(request, _('Chapter deleted.'))
    return redirect('novels:novel_detail', pk=novel.pk)


@login_required
@require_POST
def chapter_reorder(request, novel_pk, pk, direction):
    """Move a chapter up or down by one position (E6)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))

    chapter = get_object_or_404(Chapter, pk=pk, novel=novel)
    if direction == 'up':
        target = novel.chapters.active().filter(order__lt=chapter.order).order_by('-order').first()
    elif direction == 'down':
        target = novel.chapters.active().filter(order__gt=chapter.order).order_by('order').first()
    else:
        raise Http404()

    if target is not None:
        NovelService.reorder_chapter(chapter, target.order)
        messages.success(request, _('Chapter order updated.'))
    return redirect('novels:novel_detail', pk=novel.pk)


# ---------------------------------------------------------------- discovery: rankings, recent

def ranking(request):
    """Leaderboard page with several ranking modes (B6 extension)."""
    mode = request.GET.get('mode', 'popular')
    base = Novel.objects.published().select_related('author', 'category').annotate(
        favorite_count=Count('favorites', distinct=True),
        comment_count=Count('chapters__comments', distinct=True),
        avg_rating=Avg('ratings__score'),
    )
    mode_map = {
        'popular': ('-favorite_count', '-updated_at'),
        'views': ('-view_count', '-updated_at'),
        'rating': ('-avg_rating', '-updated_at'),
        'comments': ('-comment_count', '-updated_at'),
        'newest': ('-created_at',),
    }
    novels = base.order_by(*mode_map.get(mode, mode_map['popular']))[:50]
    context = {'novels': novels, 'mode': mode}
    return render(request, 'novels/ranking.html', context)


def recent_updates(request):
    """Latest chapter updates across all published novels (B1 extension)."""
    today = timezone.now().date()
    chapters = (
        Chapter.objects.active()
        .filter(novel__is_published=True, is_draft=False)
        .select_related('novel', 'novel__author')
        .order_by('-created_at')[:60]
    )
    todays = [c for c in chapters if timezone.localtime(c.created_at).date() == today]
    context = {'chapters': chapters, 'todays_count': len(todays)}
    return render(request, 'novels/recent.html', context)


def chapter_toc(request, pk):
    """Standalone table of contents grouped by volume (C3 extension)."""
    novel = get_object_or_404(Novel.objects.select_related('author'), pk=pk)
    is_author_or_admin = author_or_admin.can_edit(novel, request.user)
    if not novel.is_published and not is_author_or_admin:
        raise Http404(_('Novel not found.'))
    visible_qs = novel.chapters.filter(is_active=True)
    if not is_author_or_admin:
        visible_qs = visible_qs.filter(is_draft=False)
    volumes = novel.volumes.all()
    chapters = visible_qs.order_by('order')
    context = {'novel': novel, 'volumes': volumes, 'chapters': chapters}
    return render(request, 'novels/toc.html', context)


# ---------------------------------------------------------------- author dashboard / outline

@login_required
def dashboard(request):
    """Author dashboard: per-novel favorites/comments/views (E8)."""
    novels = (
        Novel.objects.filter(author=request.user)
        .annotate(
            favorite_count=Count('favorites', distinct=True),
            comment_count=Count('chapters__comments', distinct=True),
            total_views=F('view_count'),
        )
        .order_by('-updated_at')
    )
    return render(request, 'novels/dashboard.html', {'novels': novels})


@login_required
def outline_list(request, novel_pk):
    """List outline items for a novel (writing workspace, minimal)."""
    from interaction.models import OutlineItem
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))
    items = novel.outline.all()
    return render(request, 'novels/outline_list.html', {'novel': novel, 'items': items})


@login_required
@require_POST
def outline_create(request, novel_pk):
    """Create an outline item (writing workspace, minimal)."""
    from interaction.models import OutlineItem
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))
    title = request.POST.get('title', '').strip()
    if title:
        order = (novel.outline.count() or 0) + 1
        OutlineItem.objects.create(
            novel=novel, title=title, body=request.POST.get('body', ''), order=order)
        messages.success(request, _('Outline item added.'))
    return redirect('novels:outline_list', novel_pk=novel.pk)


# ---------------------------------------------------------------- volumes

@login_required
@require_POST
def volume_create(request, novel_pk):
    """Create a volume/part for a novel (C4)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))
    title = request.POST.get('title', '').strip()
    if title:
        order = (novel.volumes.count() or 0) + 1
        Volume.objects.create(novel=novel, title=title, order=order)
        messages.success(request, _('Volume added.'))
    return redirect('novels:novel_detail', pk=novel.pk)


# ---------------------------------------------------------------- chapter draft / schedule

@login_required
@require_POST
def chapter_toggle_draft(request, novel_pk, pk):
    """Toggle a chapter between draft and visible (C6 draft state)."""
    novel = get_object_or_404(Novel, pk=novel_pk)
    if not author_or_admin.can_edit(novel, request.user):
        return HttpResponseForbidden(_('You are not allowed to edit this novel.'))
    chapter = get_object_or_404(Chapter, pk=pk, novel=novel)
    chapter.is_draft = not chapter.is_draft
    chapter.save(update_fields=['is_draft'])
    messages.success(request, _('Chapter visibility updated.'))
    return redirect('novels:novel_detail', pk=novel.pk)
