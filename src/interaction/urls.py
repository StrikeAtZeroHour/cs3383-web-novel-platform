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
]
