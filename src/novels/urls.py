"""URL patterns for the novels app (browsing + authoring)."""

from django.urls import path

from . import views

app_name = 'novels'

urlpatterns = [
    # --- Browsing (B1-B7, C4) ---
    path('', views.home, name='home'),
    path('novels/', views.novel_list, name='novel_list'),
    path('novels/<int:pk>/', views.novel_detail, name='novel_detail'),
    path(
        'novels/<int:novel_pk>/chapters/<int:order>/',
        views.chapter_read,
        name='chapter_read',
    ),

    # --- Authoring: novels (E1-E4, E7) ---
    path('my/novels/', views.my_novels, name='my_novels'),
    path('my/novels/new/', views.novel_create, name='novel_create'),
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
