"""URL configuration for the Web Novel Platform.

The site is served at unprefixed URLs (`/`, `/novels/`, ...) and the interface
language is chosen from the navbar switcher (stored in the
`django_language` cookie). For that reason the routes are plain `path()`s
rather than `i18n_patterns()`:

* `i18n_patterns(..., prefix_default_language=False)` cannot be used here,
  because Django resolves `LocalePrefixPattern` against the *currently active*
  language. After switching to Chinese the unprefixed path no longer matches
  (the pattern expects a `zh-hant/` prefix) and every page returns 404.
* `LocaleMiddleware` is still needed (see `config/middleware.py`) so that the
  cookie drives translation and the `Content-Language` header.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import set_language

urlpatterns = [
    # Language switcher endpoint (POST from the navbar <select>)
    path('i18n/setlang/', set_language, name='set_language'),
    path('admin/', admin.site.urls),
    # Public site
    path('', include('novels.urls')),
    path('accounts/', include('accounts.urls')),
    path('', include('interaction.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
