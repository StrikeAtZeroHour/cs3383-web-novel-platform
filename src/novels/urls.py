"""URL patterns for the novels app (browsing + authoring)."""

from django.urls import path

from . import api, views

app_name = 'novels'

urlpatterns = [
    # --- Browsing (B1-B7, C4) ---
    path('', views.home, name='home'),
    # --- Read-only JSON API ---
    path('api/novels/', api.novel_list_json, name='api_novel_list'),
    path('api/novels/<int:pk>/', api.novel_detail_json, name='api_novel_detail'),
    path('novels/', views.novel_list, name='novel_list'),
    path('rankings/', views.ranking, name='ranking'),
    path('recent/', views.recent_updates, name='recent_updates'),
    path('novels/<int:pk>/', views.novel_detail, name='novel_detail'),
    path('novels/<int:pk>/toc/', views.chapter_toc, name='chapter_toc'),
    path(
        'novels/<int:novel_pk>/chapters/<int:order>/',
        views.chapter_read,
        name='chapter_read',
    ),

    # --- Authoring: novels (E1-E4, E7) ---
    path('my/dashboard/', views.dashboard, name='dashboard'),
    path('my/novels/', views.my_novels, name='my_novels'),
    path('my/novels/new/', views.novel_create, name='novel_create'),
    path('my/novels/<int:novel_pk>/volumes/new/', views.volume_create, name='volume_create'),
    path('my/novels/<int:novel_pk>/outline/', views.outline_list, name='outline_list'),
    path('my/novels/<int:novel_pk>/outline/new/', views.outline_create, name='outline_create'),
    path(
        'my/novels/<int:novel_pk>/chapters/<int:pk>/toggle-draft/',
        views.chapter_toggle_draft,
        name='chapter_toggle_draft',
    ),
    path('my/novels/<int:pk>/edit/', views.novel_edit, name='novel_edit'),
    path('my/novels/<int:pk>/delete/', views.novel_delete, name='novel_delete'),
    path('my/novels/<int:pk>/publish/', views.novel_publish, name='novel_publish'),

    # --- Authoring: chapters (E5, E6) ---
    path(
        'my/novels/<int:novel_pk>/chapters/new/',
        views.chapter_create,
        name='chapter_create',
    ),
    path(
        'my/novels/<int:novel_pk>/chapters/<int:pk>/edit/',
        views.chapter_edit,
        name='chapter_edit',
    ),
    path(
        'my/novels/<int:novel_pk>/chapters/<int:pk>/delete/',
        views.chapter_delete,
        name='chapter_delete',
    ),
    path(
        'my/novels/<int:novel_pk>/chapters/<int:pk>/move/<str:direction>/',
        views.chapter_reorder,
        name='chapter_reorder',
    ),
]
