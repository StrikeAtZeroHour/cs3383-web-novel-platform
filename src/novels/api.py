"""Read-only JSON API for the catalogue (lightweight, DRF-free).

Serves published novels and their visible chapters as JSON. Intended for
discovery/metadata integration, not bulk distribution of private data.
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import Novel


def _novel_payload(novel):
    return {
        'id': novel.pk,
        'title': novel.title,
        'author': novel.author.username,
        'category': novel.category.label,
        'status': novel.status,
        'summary': novel.summary,
        'view_count': novel.view_count,
        'word_count': novel.word_count,
        'tags': [t.name for t in novel.tags.all()],
        'updated_at': novel.updated_at.isoformat(),
    }


def novel_list_json(request):
    """GET /api/novels/ -> published novels (metadata only)."""
    novels = (
        Novel.objects.published()
        .select_related('author', 'category')
        .order_by('-updated_at')[:100]
    )
    return JsonResponse({'results': [_novel_payload(n) for n in novels]})


def novel_detail_json(request, pk):
    """GET /api/novels/<pk>/ -> one published novel with chapter list."""
    novel = get_object_or_404(
        Novel.objects.published().select_related('author', 'category'), pk=pk)
    payload = _novel_payload(novel)
    payload['chapters'] = [
        {'order': c.order, 'title': c.title, 'word_count': c.word_count}
        for c in novel.chapters.filter(is_active=True, is_draft=False).order_by('order')
    ]
    return JsonResponse(payload)
