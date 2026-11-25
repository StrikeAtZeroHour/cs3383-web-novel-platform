"""URL patterns for the accounts app (authentication + profile)."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # --- Authentication (A1, A2, A5) ---
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            success_url='/accounts/profile/',
        ),
        name='password_change',
    ),
    # --- Profile (A3, A4) ---
    path('profile/', views.my_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='profile_edit'),
    path('users/<str:username>/', views.author_profile, name='author_profile'),

    # --- Password reset (extension) ---
    path(
        'password/reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.txt',
            success_url='/accounts/password/reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/password/change/',
        ),
        name='password_reset_confirm',
    ),

    # --- Email verification (lightweight, extension) ---
    path('verify-email/', views.verify_email, name='verify_email'),
]
