"""URL patterns for the interaction app (favorites, comments, ratings)."""

from django.urls import path

from . import views

app_name = 'interaction'

urlpatterns = [
    # --- Favorites (D1, D2) ---
    path(
        'novels/<int:novel_pk>/favorite/',
        views.favorite_toggle,
        name='favorite_toggle',
    ),
    path('my/favorites/', views.my_favorites, name='my_favorites'),

    # --- Comments (D3, D4, D6) ---
    path(
        'novels/<int:novel_pk>/chapters/<int:order>/comments/',
        views.comment_create,
        name='comment_create',
    ),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment_delete'),

    # --- Ratings (D7) ---
    path('novels/<int:novel_pk>/rate/', views.rate_novel, name='rate_novel'),

    # --- Comment likes ---
    path('comments/<int:pk>/like/', views.comment_like_toggle, name='comment_like'),

    # --- Follow ---
    path('users/<str:username>/follow/', views.follow_toggle, name='follow_toggle'),

    # --- Notifications ---
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/read/', views.notification_read_all, name='notifications_read'),

    # --- Reports ---
    path('novels/<int:novel_pk>/report/', views.report_create, name='report_create'),
]
