"""On-demand translation of user-generated text (comments, discussions).

Interface text is already localised with gettext; this module handles the
*content* the users write (comments, replies, discussion posts). When a reader
asks to translate a post, the server calls a free online translator and returns
the result to the current UI language, mirroring the "Translate" button on
x.com.

The dependency (`deep-translator`) is optional at runtime: if it is missing or
the upstream service fails, `translate_text` raises `TranslationError` and the
view returns a friendly message instead of a 500.
"""

import hashlib
import logging

from django.core.cache import cache
from django.utils import translation

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when the text cannot be translated (missing lib, network, ...)."""


# Normalised Django language code -> Google Translate language code.
_LANGUAGE_MAP = {
    'en': 'en',
    'zh-hant': 'zh-TW',
    'zh-hans': 'zh-CN',
    'zh': 'zh-TW',
}

# Cache small, repeated requests (e.g. a user toggling back and forth).
_CACHE_TTL = 60 * 60 * 24


def target_language_code() -> str:
    """Return the Google-Translate code for the currently active UI language."""
    active = translation.get_language() or 'en'
    return _LANGUAGE_MAP.get(active, active.split('-')[0])


def _cache_key(text: str, target: str) -> str:
    digest = hashlib.md5(f'{target}:{text}'.encode('utf-8')).hexdigest()
    return f'bt:{target}:{digest}'


def translate_text(text: str, target: str | None = None) -> str:
    """Translate `text` into `target` (defaults to the active UI language).

    `source='auto'` lets the translator detect the input language. Results are
    cached in Django's cache framework keyed by a hash of the content so the
    same comment is only translated once per language.
    """
    text = (text or '').strip()
    if not text:
        return ''
    target = target or target_language_code()
    if not target:
        raise TranslationError('No target language available.')

    cache_key = _cache_key(text, target)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from deep_translator import GoogleTranslator
    except Exception as exc:  # pragma: no cover - import guard
        raise TranslationError('Translation service is unavailable.') from exc

    try:
        result = GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as exc:
        logger.warning('Translation failed (%s -> %s): %s', 'auto', target, exc)
        raise TranslationError('Translation failed. Please try again later.') from exc

    if not result:
        raise TranslationError('Translation returned no text.')

    cache.set(cache_key, result, _CACHE_TTL)
    return result
