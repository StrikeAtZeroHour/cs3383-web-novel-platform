"""Locale middleware that follows the user's cookie / Accept-Language.

Django's stock `LocaleMiddleware` hard-codes `LANGUAGE_CODE` for every request
whose URL carries no language prefix (see
`django.middleware.locale.LocaleMiddleware.process_request` and the
`prefix_default_language=False` branch). This project serves the whole site at
unprefixed URLs (`/`, `/novels/`, ...) and lets the navbar switcher decide the
language (stored in the `django_language` cookie), so the cookie must win.

The class below overrides only the two hooks that matter: it activates the
language requested by the user and writes `Content-Language` / `Vary` on the
response. It never redirects to a language-prefixed URL.
"""

from django.middleware.locale import LocaleMiddleware as DjangoLocaleMiddleware
from django.utils import translation
from django.utils.cache import patch_vary_headers


class LocaleMiddleware(DjangoLocaleMiddleware):
    """Activate the language requested by cookie or Accept-Language."""

    def process_request(self, request):
        language = translation.get_language_from_request(request, check_path=False)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        response.headers.setdefault("Content-Language", translation.get_language())
        patch_vary_headers(response, ("Accept-Language", "Cookie"))
        return response
