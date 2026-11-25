"""Tests for the pure SECRET_KEY / ALLOWED_HOSTS helpers in settings."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import _parse_hosts, _resolve_secret_key


class SecretKeyResolutionTests(SimpleTestCase):
    def test_provided_key_is_used(self):
        self.assertEqual(_resolve_secret_key('from-env', debug=False), 'from-env')

    def test_debug_falls_back_to_dev_key(self):
        key = _resolve_secret_key(None, debug=True)
        self.assertTrue(key.startswith('django-insecure'))

    def test_production_without_key_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            _resolve_secret_key(None, debug=False)


class ParseHostsTests(SimpleTestCase):
    def test_splits_and_drops_empty(self):
        self.assertEqual(
            _parse_hosts('example.com,,testserver,'),
            ['example.com', 'testserver'],
        )
