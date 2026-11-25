"""Admin for the accounts app (F1)."""

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'created_at', 'updated_at')
    search_fields = ('user__username', 'nickname', 'bio')
