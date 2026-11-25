"""Registration, profile and author-page views (A1-A4)."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from novels.models import Novel

from .forms import ProfileForm, RegisterForm
from .models import Profile


def register(request):
    """Create an account and log the new user in (A1)."""
    if request.user.is_authenticated:
        return redirect('novels:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Welcome! Your account has been created.'))
            return redirect('novels:home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def my_profile(request):
    """Own profile page with tabbed novels + favorites (A3, D2)."""
    from interaction.models import Favorite

    published = Novel.objects.published().filter(author=request.user)
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related('novel__author', 'novel__category')
        .order_by('-created_at')
    )
    tab = request.GET.get('tab', 'works')
    context = {
        'profile_user': request.user,
        'novels': published,
        'favorites': favorites,
        'tab': tab,
        'is_self': True,
        'follower_count': request.user.followers.count(),
        'following_count': request.user.following.count(),
    }
    return render(request, 'accounts/profile.html', context)


def author_profile(request, username):
    """Public author page: their published novels (B7)."""
    from django.contrib.auth.models import User
    from interaction.models import Follow

    user = get_object_or_404(User, username=username)
    is_self = request.user.is_authenticated and request.user.pk == user.pk
    is_following = (
        request.user.is_authenticated
        and Follow.objects.filter(follower=request.user, author=user).exists()
    )
    context = {
        'profile_user': user,
        'novels': Novel.objects.published().filter(author=user),
        'is_self': is_self,
        'is_following': is_following,
        'follower_count': user.followers.count(),
        'following_count': user.following.count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edit nickname / bio / avatar (A4)."""
    profile, _created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated.'))
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def verify_email(request):
    """Mark the current user's email as verified (lightweight extension).

    A full flow would send a signed token by email; for this prototype the
    signed-in user can confirm their own address in one click.
    """
    profile, _created = Profile.objects.get_or_create(user=request.user)
    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        messages.success(request, _('Email verified.'))
    return redirect('accounts:profile')
