"""Django Admin (F1) with takedown actions (F2).

Takedown is NOT deletion: novels are hidden with `is_published=False`,
chapters/comments with `is_active=False`, so the data can be restored.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Comment,
    Discussion,
    DiscussionReply,
    Favorite,
    Rating,
    Report,
)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'novel', 'created_at')
    search_fields = ('user__username', 'novel__title')
    list_filter = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'chapter', 'short_content', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'content', 'chapter__title')
    actions = ('takedown_comments', 'restore_comments')

    @admin.display(description=_('Content'))
    def short_content(self, obj):
        return obj.content[:60]

    @admin.action(description=_('Takedown selected comments (hide)'))
    def takedown_comments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _('%(count)s comment(s) hidden.') % {'count': updated})

    @admin.action(description=_('Restore selected comments'))
    def restore_comments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _('%(count)s comment(s) restored.') % {'count': updated})


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'novel', 'score', 'created_at', 'updated_at')
    list_filter = ('score',)
    search_fields = ('user__username', 'novel__title')


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'novel', 'chapter', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'body', 'user__username', 'novel__title')
    actions = ('takedown_discussions', 'restore_discussions')

    @admin.action(description=_('Takedown selected discussions (hide)'))
    def takedown_discussions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, _('%(count)s discussion(s) hidden.') % {'count': updated})

    @admin.action(description=_('Restore selected discussions'))
    def restore_discussions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request, _('%(count)s discussion(s) restored.') % {'count': updated})


@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'user', 'short_content', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('content', 'user__username', 'discussion__title')

    @admin.display(description=_('Content'))
    def short_content(self, obj):
        return obj.content[:60]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('pk', 'reporter', 'novel', 'comment', 'discussion', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reason', 'reporter__username')
