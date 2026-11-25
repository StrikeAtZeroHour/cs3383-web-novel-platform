"""Django Admin (F1) with takedown actions (F2)."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Chapter, Novel
from .services import NovelService


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'novel_count')
    search_fields = ('name',)

    @admin.display(description=_('Novels'))
    def novel_count(self, obj):
        return obj.novels.count()


class ChapterInline(admin.TabularInline):
    model = Chapter
    fields = ('order', 'title', 'is_active')
    extra = 0


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'category',
        'status',
        'is_published',
        'updated_at',
    )
    list_filter = ('is_published', 'status', 'category')
    search_fields = ('title', 'author__username', 'summary')
    inlines = (ChapterInline,)
    actions = ('takedown_novels', 'restore_novels')

    @admin.action(description=_('Takedown selected novels (unpublish)'))
    def takedown_novels(self, request, queryset):
        count = 0
        for novel in queryset:
            NovelService.unpublish(novel)
            count += 1
        self.message_user(request, _('%(count)s novel(s) taken down.') % {'count': count})

    @admin.action(description=_('Restore selected novels (publish)'))
    def restore_novels(self, request, queryset):
        count = 0
        for novel in queryset:
            NovelService.publish(novel)
            count += 1
        self.message_user(request, _('%(count)s novel(s) restored.') % {'count': count})


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('novel', 'order', 'title', 'is_active', 'created_at')
    list_filter = ('is_active', 'novel')
    search_fields = ('title', 'content', 'novel__title')
    ordering = ('novel', 'order')
    actions = ('takedown_chapters', 'restore_chapters')

    @admin.action(description=_('Takedown selected chapters (hide)'))
    def takedown_chapters(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _('%(count)s chapter(s) hidden.') % {'count': updated})

    @admin.action(description=_('Restore selected chapters'))
    def restore_chapters(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _('%(count)s chapter(s) restored.') % {'count': updated})
