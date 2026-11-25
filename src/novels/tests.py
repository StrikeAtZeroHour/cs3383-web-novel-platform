"""Tests for the novels app, focusing on the gettext/i18n behaviour."""

from django.test import Client, TestCase
from django.utils import translation

from .models import Category, Novel
from .services import NovelService


class CategoryTranslationTests(TestCase):
    """Category labels come from gettext, never from the database (B4)."""

    def setUp(self):
        self.category = Category.objects.create(name='Fantasy')

    def test_database_stores_english_only(self):
        self.assertEqual(self.category.name, 'Fantasy')
        self.assertEqual(Category.objects.get(pk=self.category.pk).name, 'Fantasy')

    def test_label_is_translated_by_active_language(self):
        with translation.override('en'):
            self.assertEqual(self.category.label, 'Fantasy')
        with translation.override('zh-hant'):
            self.assertEqual(self.category.label, '奇幻')

    def test_str_follows_active_language(self):
        with translation.override('zh-hant'):
            self.assertEqual(str(self.category), '奇幻')
            self.assertEqual(Category.objects.get(pk=self.category.pk).__str__(), '奇幻')

    def test_label_falls_back_to_english_for_unknown_names(self):
        other = Category.objects.create(name='Not A Seeded Category')
        with translation.override('zh-hant'):
            self.assertEqual(other.label, 'Not A Seeded Category')


class LanguageSwitchTests(TestCase):
    """The navbar switcher must change the whole interface."""

    def setUp(self):
        self.category = Category.objects.create(name='Fantasy')
        author = self._make_author()
        self.novel = Novel.objects.create(
            author=author, category=self.category, title='A Test Novel'
        )
        NovelService.publish(self.novel)
        self.client = Client()

    @staticmethod
    def _make_author():
        from django.contrib.auth.models import User

        return User.objects.create_user(username='tester', password='pw12345678')

    def test_switch_language_cookie_renders_translated_home(self):
        response = self.client.post(
            '/i18n/setlang/', {'language': 'zh-hant', 'next': '/'}
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Language'], 'zh-hant')
        html = response.content.decode('utf-8')
        self.assertIn('奇幻', html)
        self.assertNotIn('Fantasy', html)
        self.assertIn('瀏覽作品', html)

    def test_switch_language_back_to_english(self):
        self.client.cookies['django_language'] = 'zh-hant'
        self.client.post('/i18n/setlang/', {'language': 'en', 'next': '/'})

        response = self.client.get('/')
        self.assertEqual(response['Content-Language'], 'en')
        html = response.content.decode('utf-8')
        self.assertIn('Fantasy', html)
        self.assertNotIn('奇幻', html)

    def test_novel_content_is_never_translated(self):
        self.client.cookies['django_language'] = 'zh-hant'
        response = self.client.get(f'/novels/{self.novel.pk}/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('A Test Novel', html)
        self.assertIn('奇幻', html)

    def test_unprefixed_urls_resolve_in_both_languages(self):
        for language in ('en', 'zh-hant'):
            self.client.cookies['django_language'] = language
            for url in ('/', '/novels/'):
                with self.subTest(language=language, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
