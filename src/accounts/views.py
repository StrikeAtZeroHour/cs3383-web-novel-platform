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
    """Own profile page with the user's published novels (A3)."""
    published = Novel.objects.published().filter(author=request.user)
    context = {
        'profile_user': request.user,
        'novels': published,
        'is_self': True,
    }
    return render(request, 'accounts/profile.html', context)


def author_profile(request, username):
    """Public author page: their published novels (B7)."""
    from django.contrib.auth.models import User

    user = get_object_or_404(User, username=username)
    context = {
        'profile_user': user,
        'novels': Novel.objects.published().filter(author=user),
        'is_self': request.user.is_authenticated and request.user.pk == user.pk,
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
