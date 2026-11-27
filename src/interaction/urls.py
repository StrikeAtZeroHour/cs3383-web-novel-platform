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

    # --- Translation (like x.com "Translate") ---
    path(
        'comments/<int:pk>/translate/',
        views.comment_translate,
        name='comment_translate',
    ),

    # --- Follow ---
    path('users/<str:username>/follow/', views.follow_toggle, name='follow_toggle'),

    # --- Notifications ---
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/read/', views.notification_read_all, name='notifications_read'),

    # --- Reports ---
    path('novels/<int:novel_pk>/report/', views.report_create, name='report_create'),

    # --- Discussion board ---
    path('discussions/', views.discussion_list, name='discussion_list'),
    path('discussions/new/', views.discussion_create, name='discussion_create'),
    path('discussions/<int:pk>/', views.discussion_detail, name='discussion_detail'),
    path('discussions/<int:pk>/reply/', views.discussion_reply, name='discussion_reply'),
    path('discussions/<int:pk>/like/', views.discussion_like_toggle, name='discussion_like'),
    path('discussions/<int:pk>/delete/', views.discussion_delete, name='discussion_delete'),
    path('discussions/<int:pk>/report/', views.discussion_report, name='discussion_report'),
    path(
        'discussion-replies/<int:pk>/like/',
        views.discussion_reply_like_toggle,
        name='discussion_reply_like',
    ),
]
