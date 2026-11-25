"""Models for the accounts app.

`User` is Django's built-in `auth.User` (extended, not replaced).
`Profile` holds the extra display fields and is created automatically by a
`post_save` signal. `User.is_admin()` is the single source of truth for the
"administrator" role across the whole project.
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


def _is_admin(self) -> bool:
    """Single authoritative check for the administrator role (F1, A6)."""
    return bool(self.is_staff or self.is_superuser)


User.is_admin = _is_admin


class Profile(models.Model):
    """Extra public information about a user (A3, A4)."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    nickname = models.CharField(_('Nickname'), max_length=50, blank=True)
    bio = models.TextField(_('Bio'), blank=True)
    avatar = models.ImageField(
        _('Avatar'),
        upload_to='avatars/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __str__(self) -> str:
        return f'{self.display_name} ({self.user.username})'

    @property
    def display_name(self) -> str:
        """Nickname if set, otherwise the login username."""
        return self.nickname or self.user.username

    def get_absolute_url(self) -> str:
        from django.urls import reverse

        return reverse('accounts:author_profile', args=[self.user.username])


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Every user gets a Profile at registration time (see `02-class-diagram.md`)."""
    if created:
        Profile.objects.create(user=instance)
