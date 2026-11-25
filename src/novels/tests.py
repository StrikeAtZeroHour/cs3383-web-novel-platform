"""Tests for the novels app, focusing on the gettext/i18n behaviour."""

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, TestCase
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


# ---------------------------------------------------------------------------
# Behavioural tests for the novels app.
#
# Each test maps to a row of the S2 inventory (see TEST_COVERAGE.md).
# Row keys:
#   NOV-ORDER  NOV-PREVNEXT  NOV-ORDER-MAX  NOV-CREATE  NOV-UPDATE
#   NOV-DELETE NOV-PUBLISH   NOV-PERMISSION NOV-VALIDATION
#   NOV-PAGINATION NOV-SEARCH NOV-FILTER NOV-SORT NOV-AGGREGATION
#   NOV-CHAPTER-ORDER NOV-READ NOV-GUEST
# ---------------------------------------------------------------------------
from django.contrib.auth.models import User  # noqa: E402
from .models import Chapter  # noqa: E402


def _user(username='author', password='pw12345678', **extra):
    return User.objects.create_user(username=username, password=password, **extra)


def _novel(author, category, title='Novel', published=False):
    return Novel.objects.create(
        author=author, category=category, title=title, is_published=published)


class NovelOrderingModelTests(TestCase):
    """NOV-ORDER / NOV-ORDER-MAX: chapter numbering rules."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat)

    def test_first_chapter_gets_order_one(self):
        # NOV-ORDER-MAX - empty boundary
        self.assertEqual(self.novel.get_next_order(), 1)

    def test_next_order_is_max_plus_one(self):
        # NOV-ORDER-MAX - consecutive
        NovelService.create_chapter(self.novel, title='a', content='x')
        NovelService.create_chapter(self.novel, title='b', content='x')
        self.assertEqual(self.novel.get_next_order(), 3)

    def test_next_order_counts_soft_deleted_rows(self):
        # NOV-ORDER-MAX - soft-deleted rows still reserve numbers
        a = NovelService.create_chapter(self.novel, title='a', content='x')
        NovelService.create_chapter(self.novel, title='b', content='x')
        NovelService.delete_chapter(a)
        self.assertEqual(self.novel.get_next_order(), 3)


class ChapterNavigationModelTests(TestCase):
    """NOV-PREVNEXT: previous/next active chapter resolution."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat)
        self.c1 = NovelService.create_chapter(self.novel, title='1', content='x')
        self.c2 = NovelService.create_chapter(self.novel, title='2', content='x')

    def test_first_chapter_has_no_previous(self):
        # NOV-PREVNEXT - lower boundary
        self.assertIsNone(self.c1.get_prev_chapter())

    def test_second_chapter_points_previous_to_first(self):
        # NOV-PREVNEXT - happy path
        self.assertEqual(self.c2.get_prev_chapter().pk, self.c1.pk)

    def test_last_chapter_has_no_next(self):
        # NOV-PREVNEXT - upper boundary
        self.assertIsNone(self.c2.get_next_chapter())

    def test_inactive_chapter_is_skipped_in_navigation(self):
        # NOV-PREVNEXT - inactive chapter excluded
        self.c1.is_active = False
        self.c1.save(update_fields=['is_active'])
        self.assertIsNone(self.c2.get_prev_chapter())


class NovelServicePublishTests(TestCase):
    """NOV-PUBLISH: publish/unpublish toggles visibility and keeps data."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat)

    def test_publish_sets_published_true(self):
        # NOV-PUBLISH - asserts DB state
        NovelService.publish(self.novel)
        self.novel.refresh_from_db()
        self.assertTrue(self.novel.is_published)

    def test_unpublish_keeps_chapters(self):
        # NOV-PUBLISH - data retained on unpublish
        NovelService.create_chapter(self.novel, title='c', content='x')
        NovelService.publish(self.novel)
        NovelService.unpublish(self.novel)
        self.novel.refresh_from_db()
        self.assertFalse(self.novel.is_published)
        self.assertEqual(self.novel.chapters.count(), 1)


class NovelServiceReorderTests(TestCase):
    """NOV-CHAPTER-ORDER: reordering shifts siblings without collisions."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat)
        self.a = NovelService.create_chapter(self.novel, title='A', content='x')
        self.b = NovelService.create_chapter(self.novel, title='B', content='x')
        self.c = NovelService.create_chapter(self.novel, title='C', content='x')

    def test_move_chapter_down_shifts_next_up(self):
        # NOV-CHAPTER-ORDER - swap first with second
        NovelService.reorder_chapter(self.a, self.b.order)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.order, 2)
        self.assertEqual(self.b.order, 1)

    def test_reorder_clamps_below_one(self):
        # NOV-CHAPTER-ORDER - lower clamp boundary
        NovelService.reorder_chapter(self.b, 0)
        self.b.refresh_from_db()
        self.assertEqual(self.b.order, 1)

    def test_orders_remain_unique_after_reorder(self):
        # NOV-CHAPTER-ORDER - invariant: no duplicate order values when a
        # chapter is moved to an earlier position (regression for D-001).
        NovelService.reorder_chapter(self.c, 1)
        orders = list(
            Chapter.objects.filter(novel=self.novel).values_list('order', flat=True))
        self.assertEqual(len(orders), len(set(orders)))
        self.c.refresh_from_db()
        self.assertEqual(self.c.order, 1)


class NovelServiceDeleteTests(TestCase):
    """NOV-DELETE: deleting a novel cascades to children."""

    def test_delete_novel_removes_chapters(self):
        # NOV-DELETE - cascade, asserts DB state
        user = _user()
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(user, cat)
        NovelService.create_chapter(novel, title='c', content='x')
        pk = novel.pk
        NovelService.delete_novel(novel)
        self.assertFalse(Novel.objects.filter(pk=pk).exists())
        self.assertEqual(Chapter.objects.filter(novel_id=pk).count(), 0)


class NovelCreateViewTests(TestCase):
    """NOV-CREATE: creating a novel sets author from server and unpublished."""

    def setUp(self):
        self.user = _user(username='creator')
        self.cat = Category.objects.create(name='Fantasy')

    def test_create_novel_sets_author_and_unpublished(self):
        # NOV-CREATE - creation, asserts DB state
        self.client.force_login(self.user)
        response = self.client.post(
            '/my/novels/new/',
            {'title': 'Fresh', 'category': self.cat.pk, 'summary': '', 'status': 'ongoing'},
        )
        self.assertRedirects(response, '/my/novels/')
        novel = Novel.objects.get(title='Fresh')
        self.assertEqual(novel.author, self.user)
        self.assertFalse(novel.is_published)

    def test_create_novel_blank_title_is_rejected(self):
        # NOV-VALIDATION - empty field
        self.client.force_login(self.user)
        response = self.client.post(
            '/my/novels/new/',
            {'title': '', 'category': self.cat.pk, 'status': 'ongoing'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Novel.objects.count(), 0)

    def test_create_novel_requires_login(self):
        # NOV-PERMISSION - anonymous redirected
        response = self.client.get('/my/novels/new/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


class NovelPermissionViewTests(TestCase):
    """NOV-PERMISSION: ownership enforced on edit/delete/publish."""

    def setUp(self):
        self.owner = _user(username='owner')
        self.other = _user(username='intruder')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='Mine', published=True)

    def test_non_owner_cannot_edit_novel(self):
        # NOV-PERMISSION - access to another user's object
        self.client.force_login(self.other)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/edit/',
            {'title': 'Hacked', 'category': self.cat.pk, 'status': 'ongoing'},
        )
        self.assertEqual(response.status_code, 403)
        self.novel.refresh_from_db()
        self.assertEqual(self.novel.title, 'Mine')

    def test_non_owner_cannot_delete_novel(self):
        # NOV-PERMISSION - denied delete
        self.client.force_login(self.other)
        response = self.client.post(f'/my/novels/{self.novel.pk}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Novel.objects.filter(pk=self.novel.pk).exists())

    def test_non_owner_cannot_publish_novel(self):
        # NOV-PERMISSION - denied publish
        hidden = _novel(self.owner, self.cat, title='Hidden', published=False)
        self.client.force_login(self.other)
        response = self.client.post(f'/my/novels/{hidden.pk}/publish/')
        self.assertEqual(response.status_code, 403)
        hidden.refresh_from_db()
        self.assertFalse(hidden.is_published)

    def test_owner_can_publish_own_novel(self):
        # NOV-PUBLISH - owner path via view, asserts DB state
        hidden = _novel(self.owner, self.cat, title='Draft', published=False)
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{hidden.pk}/publish/')
        hidden.refresh_from_db()
        self.assertTrue(hidden.is_published)


class NovelListViewTests(TestCase):
    """NOV-SEARCH / NOV-FILTER / NOV-SORT / NOV-PAGINATION: list behaviour."""

    def setUp(self):
        self.user = _user()
        self.cat_f = Category.objects.create(name='Fantasy')
        self.cat_s = Category.objects.create(name='Science Fiction')
        for i in range(15):
            _novel(self.user, self.cat_f, title=f'Fantasy {i}', published=True)
        self.scifi = _novel(self.user, self.cat_s, title='SciSpace', published=True)
        self.hidden = _novel(self.user, self.cat_f, title='Secret', published=False)

    def test_list_excludes_unpublished(self):
        # NOV-SEARCH - unpublished never listed
        response = self.client.get('/novels/')
        self.assertNotContains(response, 'Secret')

    def test_search_matches_title_substring(self):
        # NOV-SEARCH - happy path
        response = self.client.get('/novels/', {'q': 'SciSpace'})
        self.assertContains(response, 'SciSpace')

    def test_filter_by_category_returns_only_that_category(self):
        # NOV-FILTER - membership
        response = self.client.get('/novels/', {'category': self.cat_s.pk})
        self.assertContains(response, 'SciSpace')
        self.assertNotContains(response, 'Fantasy 0')

    def test_sort_by_title_is_alphabetical(self):
        # NOV-SORT - ordering
        response = self.client.get('/novels/', {'sort': 'title'})
        titles = [n.title for n in response.context['page_obj']]
        self.assertEqual(titles, sorted(titles))

    def test_first_page_has_page_size_items(self):
        # NOV-PAGINATION - page size boundary
        response = self.client.get('/novels/')
        self.assertEqual(len(response.context['page_obj']), 12)

    def test_last_page_holds_remainder(self):
        # NOV-PAGINATION - last page boundary (16 published -> 12 + 4)
        response = self.client.get('/novels/', {'page': 2})
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_out_of_range_page_falls_back_to_last(self):
        # NOV-PAGINATION - empty/invalid page number
        response = self.client.get('/novels/', {'page': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)

    def test_empty_result_set_renders(self):
        # NOV-PAGINATION - empty result set
        response = self.client.get('/novels/', {'q': 'no-such-title-xyz'})
        self.assertEqual(response.status_code, 200)


class NovelDetailViewTests(TestCase):
    """NOV-READ / NOV-GUEST / NOV-AGGREGATION / NOV-UPDATE."""

    def setUp(self):
        self.owner = _user(username='owner')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='Detail', published=True)

    def test_guest_can_read_published_detail(self):
        # NOV-GUEST - anonymous read
        response = self.client.get(f'/novels/{self.novel.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail')

    def test_unpublished_detail_is_404_for_guest(self):
        # NOV-GUEST - unpublished hidden
        hidden = _novel(self.owner, self.cat, title='Hidden', published=False)
        response = self.client.get(f'/novels/{hidden.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_avg_rating_is_aggregated(self):
        # NOV-AGGREGATION - average of ratings
        from interaction.models import Rating
        u2 = _user(username='rater2')
        Rating.objects.create(user=self.owner, novel=self.novel, score=4)
        Rating.objects.create(user=u2, novel=self.novel, score=2)
        response = self.client.get(f'/novels/{self.novel.pk}/')
        self.assertEqual(response.context['avg_score'], 3)
        self.assertEqual(response.context['rating_count'], 2)

    def test_owner_can_edit_published_novel(self):
        # NOV-UPDATE - update flow, asserts DB state
        self.client.force_login(self.owner)
        self.client.post(
            f'/my/novels/{self.novel.pk}/edit/',
            {'title': 'Detail v2', 'category': self.cat.pk, 'status': 'completed'},
        )
        self.novel.refresh_from_db()
        self.assertEqual(self.novel.title, 'Detail v2')
        self.assertEqual(self.novel.status, 'completed')


class ChapterReadViewTests(TestCase):
    """NOV-READ: chapter body and navigation in the reader page."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat, published=True)
        self.c1 = NovelService.create_chapter(
            self.novel, title='One', content='first body')

    def test_guest_reads_chapter_body(self):
        # NOV-GUEST - anonymous read of chapter
        response = self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'first body')

    def test_inactive_chapter_is_404(self):
        # NOV-READ - soft-deleted chapter hidden
        self.c1.is_active = False
        self.c1.save(update_fields=['is_active'])
        response = self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.assertEqual(response.status_code, 404)

    def test_ideographic_chapter_content_is_rendered(self):
        # NOV-READ - non-latin script round-trip
        NovelService.create_chapter(
            self.novel, title='第二章', content='這是一段中文內容。')
        response = self.client.get(f'/novels/{self.novel.pk}/chapters/2/')
        self.assertContains(response, '這是一段中文內容。')


class ChapterAuthoringViewTests(TestCase):
    """NOV-CREATE / NOV-CHAPTER-ORDER / NOV-PERMISSION for chapters."""

    def setUp(self):
        self.owner = _user(username='owner')
        self.other = _user(username='intruder')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='N', published=True)

    def test_owner_adds_chapter_appended_at_next_order(self):
        # NOV-CHAPTER-ORDER - append at MAX+1, asserts DB state
        self.client.force_login(self.owner)
        self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/new/',
            {'title': 'Ch', 'content': 'body'},
        )
        chapter = Chapter.objects.get(novel=self.novel)
        self.assertEqual(chapter.order, 1)
        self.assertEqual(chapter.title, 'Ch')

    def test_non_owner_cannot_add_chapter(self):
        # NOV-PERMISSION - denied create
        self.client.force_login(self.other)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/new/',
            {'title': 'Ch', 'content': 'body'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Chapter.objects.count(), 0)

    def test_empty_chapter_content_is_rejected(self):
        # NOV-VALIDATION - empty content
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/new/',
            {'title': 'Ch', 'content': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chapter.objects.count(), 0)

    def test_reorder_up_moves_chapter_before_previous(self):
        # NOV-CHAPTER-ORDER - reorder via view
        NovelService.create_chapter(self.novel, title='A', content='x')
        b = NovelService.create_chapter(self.novel, title='B', content='x')
        self.client.force_login(self.owner)
        self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{b.pk}/move/up/')
        b.refresh_from_db()
        self.assertEqual(b.order, 1)


class NovelModelUnitTests(TestCase):
    """novels/models.py: __str__, get_chapter_count (covers lines 92, 101)."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat, title='Titled')

    def test_novel_str_is_title(self):
        # line 92: __str__ returns the title
        self.assertEqual(str(self.novel), 'Titled')

    def test_get_chapter_count_counts_active_only(self):
        # line 101: active chapters counted, soft-deleted excluded
        NovelService.create_chapter(self.novel, title='a', content='x')
        dead = NovelService.create_chapter(self.novel, title='b', content='x')
        NovelService.delete_chapter(dead)
        self.assertEqual(self.novel.get_chapter_count(), 1)


class ChapterModelUnitTests(TestCase):
    """novels/models.py: Chapter.__str__ (covers line 162)."""

    def test_chapter_str_includes_novel_and_order(self):
        # line 162: __str__ = '<novel> - Ch.<order> <title>'
        user = _user()
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(user, cat, title='Book')
        chapter = NovelService.create_chapter(novel, title='Intro', content='x')
        self.assertEqual(str(chapter), 'Book - Ch.1 Intro')


class ReorderNoopTests(TestCase):
    """novels/services.py: reorder early-return (covers line 66 + branch)."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat)
        self.chapter = NovelService.create_chapter(self.novel, title='A', content='x')

    def test_reorder_to_same_position_is_noop(self):
        # line 66: new_order == old_order -> early return, order unchanged
        NovelService.reorder_chapter(self.chapter, self.chapter.order)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.order, 1)




class NovelAdminCustomisationTests(TestCase):
    """novels/admin.py: list display + takedown/restore actions (F2)."""

    def setUp(self):
        self.user = _user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat, title='Admin Nov')
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='Ch', content='x', order=1)
        from django.contrib import admin as dj_admin
        from novels.admin import CategoryAdmin, ChapterAdmin, NovelAdmin
        self.Novel = Novel
        self.Chapter = Chapter
        self.Category = Category
        self.novel_admin = NovelAdmin(Novel, dj_admin.site)
        self.chapter_admin = ChapterAdmin(Chapter, dj_admin.site)
        self.category_admin = CategoryAdmin(Category, dj_admin.site)
        self.request = RequestFactory().get('/admin/')
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)

    def test_category_admin_novel_count(self):
        # line 17: CategoryAdmin.novel_count returns related novel count
        self.assertEqual(self.category_admin.novel_count(self.cat), 1)

    def test_novel_admin_takedown_unpublishes(self):
        # lines 43-47: takedown action unpublishes + counts
        self.Novel.objects.filter(pk=self.novel.pk).update(is_published=True)
        self.novel_admin.takedown_novels(
            self.request, self.Novel.objects.filter(pk=self.novel.pk))
        self.novel.refresh_from_db()
        self.assertFalse(self.novel.is_published)

    def test_novel_admin_restore_publishes(self):
        # lines 51-55: restore action publishes + counts
        self.novel_admin.restore_novels(
            self.request, self.Novel.objects.filter(pk=self.novel.pk))
        self.novel.refresh_from_db()
        self.assertTrue(self.novel.is_published)

    def test_chapter_admin_takedown_hides(self):
        # lines 68-69: takedown chapter sets is_active=False
        self.chapter_admin.takedown_chapters(
            self.request, self.Chapter.objects.filter(pk=self.chapter.pk))
        self.chapter.refresh_from_db()
        self.assertFalse(self.chapter.is_active)

    def test_chapter_admin_restore_shows(self):
        # lines 73-74: restore chapter sets is_active=True
        self.Chapter.objects.filter(pk=self.chapter.pk).update(is_active=False)
        self.chapter_admin.restore_chapters(
            self.request, self.Chapter.objects.filter(pk=self.chapter.pk))
        self.chapter.refresh_from_db()
        self.assertTrue(self.chapter.is_active)


class UrlConfigMediaRouteTests(TestCase):
    """config/urls.py line 33: media static route present when DEBUG."""

    def test_media_route_registered_when_debug_true(self):
        # line 33: DEBUG branch appends static(MEDIA_URL) patterns.
        # Reload the URLconf under DEBUG=True because the test runner forces
        # DEBUG=False, so the module body (line 33) would not otherwise run.
        import importlib
        from django.test import override_settings
        from django.urls import URLPattern
        from config import urls as config_urls
        with override_settings(DEBUG=True):
            importlib.reload(config_urls)
            media_patterns = [
                p for p in config_urls.urlpatterns
                if isinstance(p, URLPattern) and 'media' in p.pattern.regex.pattern
            ]
        self.assertEqual(len(media_patterns), 1)


class NovelDetailAuthenticatedTests(TestCase):
    """novels/views.py lines 99-100: authenticated user_rating + favorite."""

    def test_logged_in_user_sees_own_rating_and_favorite(self):
        # lines 99-100: authenticated branch resolves Rating and Favorite
        from interaction.models import Favorite, Rating
        user = _user(username='detuser')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(user, cat, title='Det', published=True)
        Rating.objects.create(user=user, novel=novel, score=4)
        Favorite.objects.create(user=user, novel=novel)
        self.client.force_login(user)
        response = self.client.get(f'/novels/{novel.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_favorited'])
        self.assertEqual(response.context['user_rating'].score, 4)


class ChapterReadUnpublishedTests(TestCase):
    """novels/views.py line 121: unpublished novel chapter 404 for guest."""

    def test_unpublished_chapter_novel_is_404_for_guest(self):
        # line 121: not published and not owner -> Http404
        user = _user()
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(user, cat, title='Hidden', published=False)
        NovelService.create_chapter(novel, title='c', content='x')
        response = self.client.get(f'/novels/{novel.pk}/chapters/1/')
        self.assertEqual(response.status_code, 404)


class NovelCreateGetTests(TestCase):
    """novels/views.py line 175: novel_create GET builds empty form."""

    def test_create_form_get_renders(self):
        # line 175: non-POST branch builds NovelForm()
        user = _user(username='createnew')
        self.client.force_login(user)
        response = self.client.get('/my/novels/new/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_new'])


class NovelEditGetTests(TestCase):
    """novels/views.py lines 194-196: novel_edit GET builds bound form."""

    def test_owner_gets_edit_form(self):
        # lines 194-196: non-POST branch builds NovelForm(instance=novel)
        owner = _user(username='editowner')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='E', published=True)
        self.client.force_login(owner)
        response = self.client.get(f'/my/novels/{novel.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].instance, novel)


class NovelDeleteSuccessTests(TestCase):
    """novels/views.py lines 209-211: owner deletes own novel."""

    def test_owner_deletes_own_novel(self):
        # lines 209-211: delete + message + redirect
        owner = _user(username='delowner')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='Gone', published=True)
        pk = novel.pk
        self.client.force_login(owner)
        response = self.client.post(f'/my/novels/{pk}/delete/')
        self.assertRedirects(response, '/my/novels/')
        self.assertFalse(Novel.objects.filter(pk=pk).exists())


class NovelUnpublishTests(TestCase):
    """novels/views.py lines 223-224: publishing a published novel unpublishes."""

    def test_owner_unpublishes_published_novel(self):
        # lines 222-224: is_published True -> unpublish branch
        owner = _user(username='unpubowner')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='Was', published=True)
        self.client.force_login(owner)
        self.client.post(f'/my/novels/{novel.pk}/publish/')
        novel.refresh_from_db()
        self.assertFalse(novel.is_published)


class ChapterCreateGetTests(TestCase):
    """novels/views.py line 252: chapter_create GET builds form."""

    def test_chapter_create_form_get_renders(self):
        # line 252: non-POST branch builds ChapterForm()
        owner = _user(username='chcreate')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='N', published=True)
        self.client.force_login(owner)
        response = self.client.get(f'/my/novels/{novel.pk}/chapters/new/')
        self.assertEqual(response.status_code, 200)


class ChapterEditViewTests(TestCase):
    """novels/views.py lines 260-275: chapter_edit GET/POST valid/invalid."""

    def setUp(self):
        self.owner = _user(username='chedit')
        self.other = _user(username='chintruder')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='N', published=True)
        self.chapter = NovelService.create_chapter(
            self.novel, title='Old', content='old body')

    def test_owner_gets_chapter_edit_form(self):
        # line 273: GET builds ChapterForm(instance=chapter)
        self.client.force_login(self.owner)
        response = self.client.get(
            f'/my/novels/{self.novel.pk}/chapters/{self.chapter.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chapter'], self.chapter)

    def test_owner_edits_chapter_content(self):
        # lines 265-271: valid POST saves + redirect
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{self.chapter.pk}/edit/',
            {'title': 'New', 'content': 'new body'})
        self.assertRedirects(response, f'/novels/{self.novel.pk}/')
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.title, 'New')
        self.assertEqual(self.chapter.content, 'new body')

    def test_chapter_edit_invalid_content_is_rejected(self):
        # lines 265-266: invalid POST re-renders, no save
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{self.chapter.pk}/edit/',
            {'title': '', 'content': ''})
        self.assertEqual(response.status_code, 200)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.title, 'Old')


class ChapterDeleteSuccessTests(TestCase):
    """novels/views.py lines 286-293: owner soft-deletes chapter."""

    def test_owner_deletes_chapter_soft(self):
        # lines 290-293: delete_chapter + redirect, row remains inactive
        owner = _user(username='chdel')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='N', published=True)
        chapter = NovelService.create_chapter(novel, title='c', content='x')
        self.client.force_login(owner)
        response = self.client.post(
            f'/my/novels/{novel.pk}/chapters/{chapter.pk}/delete/')
        self.assertRedirects(response, f'/novels/{novel.pk}/')
        chapter.refresh_from_db()
        self.assertFalse(chapter.is_active)


class ChapterReorderViewTests(TestCase):
    """novels/views.py lines 302, 307-310, branch 312->315: reorder paths."""

    def setUp(self):
        self.owner = _user(username='reowner')
        self.other = _user(username='reintruder')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='N', published=True)

    def test_non_owner_cannot_reorder_chapter(self):
        # line 302: permission denied -> 403
        chapter = NovelService.create_chapter(self.novel, title='A', content='x')
        self.client.force_login(self.other)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{chapter.pk}/move/up/')
        self.assertEqual(response.status_code, 403)

    def test_owner_reorders_chapter_down(self):
        # line 307: direction 'down' -> moves second chapter up
        a = NovelService.create_chapter(self.novel, title='A', content='x')
        b = NovelService.create_chapter(self.novel, title='B', content='x')
        self.client.force_login(self.owner)
        self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{a.pk}/move/down/')
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.order, 2)
        self.assertEqual(b.order, 1)

    def test_reorder_invalid_direction_is_404(self):
        # line 310: unknown direction -> Http404
        chapter = NovelService.create_chapter(self.novel, title='A', content='x')
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{chapter.pk}/move/sideways/')
        self.assertEqual(response.status_code, 404)

    def test_reorder_top_chapter_up_is_noop(self):
        # branch 312->315: target None -> no reorder, redirect only
        chapter = NovelService.create_chapter(self.novel, title='A', content='x')
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{chapter.pk}/move/up/')
        self.assertRedirects(response, f'/novels/{self.novel.pk}/')
        chapter.refresh_from_db()
        self.assertEqual(chapter.order, 1)


class NovelEditInvalidTests(TestCase):
    """novels/views.py branch 189->196: invalid novel edit re-renders."""

    def test_owner_invalid_edit_rerenders_without_saving(self):
        # branch 189 False->196: invalid form falls through to render
        owner = _user(username='badowner')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='Keep', published=True)
        self.client.force_login(owner)
        response = self.client.post(
            f'/my/novels/{novel.pk}/edit/',
            {'title': '', 'category': cat.pk, 'status': 'ongoing'})
        self.assertEqual(response.status_code, 200)
        novel.refresh_from_db()
        self.assertEqual(novel.title, 'Keep')


class ChapterEditPermissionTests(TestCase):
    """novels/views.py line 262: non-owner chapter edit forbidden."""

    def test_non_owner_cannot_edit_chapter(self):
        # line 262: can_edit False -> 403 before form handling
        owner = _user(username='ceowner')
        other = _user(username='ceother')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='N', published=True)
        chapter = NovelService.create_chapter(novel, title='c', content='x')
        self.client.force_login(other)
        response = self.client.post(
            f'/my/novels/{novel.pk}/chapters/{chapter.pk}/edit/',
            {'title': 'x', 'content': 'y'})
        self.assertEqual(response.status_code, 403)


class ChapterDeletePermissionTests(TestCase):
    """novels/views.py line 288: non-owner chapter delete forbidden."""

    def test_non_owner_cannot_delete_chapter(self):
        # line 288: can_edit False -> 403 before delete
        owner = _user(username='cdowner')
        other = _user(username='cdother')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(owner, cat, title='N', published=True)
        chapter = NovelService.create_chapter(novel, title='c', content='x')
        self.client.force_login(other)
        response = self.client.post(
            f'/my/novels/{novel.pk}/chapters/{chapter.pk}/delete/')
        self.assertEqual(response.status_code, 403)
        chapter.refresh_from_db()
        self.assertTrue(chapter.is_active)


class NovelDefaultVisibilityTests(TestCase):
    """novels/models.py: Novel.is_published defaults to False (unpublished)."""

    def test_new_novel_defaults_to_unpublished(self):
        # pins the model default, which novel_create also sets explicitly
        user = _user(username='defuser')
        cat = Category.objects.create(name='Fantasy')
        novel = Novel.objects.create(author=user, category=cat, title='Def')
        self.assertFalse(novel.is_published)


class NovelListDefaultOrderTests(TestCase):
    """novels/views.py: default sort orders by most-recently-updated first."""

    def test_default_order_is_most_recently_updated_first(self):
        # pins the 'updated' sort clause (-updated_at): later-updated first
        user = _user(username='orderuser')
        cat = Category.objects.create(name='Fantasy')
        old = _novel(user, cat, title='Old', published=True)
        new = _novel(user, cat, title='New', published=True)
        from django.utils import timezone
        from datetime import timedelta
        Novel.objects.filter(pk=old.pk).update(
            updated_at=timezone.now() - timedelta(days=2))
        Novel.objects.filter(pk=new.pk).update(updated_at=timezone.now())
        response = self.client.get('/novels/')
        titles = [n.title for n in response.context['page_obj']]
        self.assertLess(titles.index('New'), titles.index('Old'))


class NewFeatureViewsTests(TestCase):
    """Coverage + behaviour for the extended feature set."""

    def setUp(self):
        from interaction.models import Follow, Notification, OutlineItem, Report
        self.owner = _user(username='featuser')
        self.other = _user(username='otheruser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='Feat', published=True)
        self.chapter = NovelService.create_chapter(
            self.novel, title='C1', content='hello world')

    # --- word count / view count ---
    def test_chapter_word_count_computed_on_save(self):
        self.assertEqual(self.chapter.word_count, 2)  # 'hello world'

    def test_cjk_word_count_counts_per_character(self):
        from novels.models import Chapter
        self.assertEqual(Chapter.count_words('龍族傳奇'), 4)

    def test_novel_detail_increments_view_count_for_visitors(self):
        self.client.get(f'/novels/{self.novel.pk}/')
        self.novel.refresh_from_db()
        self.assertEqual(self.novel.view_count, 1)

    def test_chapter_read_increments_chapter_view_count(self):
        self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.view_count, 1)

    # --- ranking / recent / toc ---
    def test_ranking_page_lists_published(self):
        for mode in ('popular', 'views', 'rating', 'comments', 'newest'):
            r = self.client.get(f'/rankings/?mode={mode}')
            self.assertEqual(r.status_code, 200)

    def test_recent_updates_page(self):
        r = self.client.get('/recent/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Feat')

    def test_toc_page(self):
        r = self.client.get(f'/novels/{self.novel.pk}/toc/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'C1')

    def test_toc_unpublished_hidden_from_guest(self):
        hidden = _novel(self.owner, self.cat, title='H', published=False)
        r = self.client.get(f'/novels/{hidden.pk}/toc/')
        self.assertEqual(r.status_code, 404)

    # --- tag / status / min_words filter ---
    def test_filter_by_tag(self):
        from novels.models import Tag
        tag = Tag.objects.create(name='magic')
        self.novel.tags.add(tag)
        r = self.client.get('/novels/', {'tag': 'magic'})
        self.assertContains(r, 'Feat')
        r2 = self.client.get('/novels/', {'tag': 'nope'})
        self.assertNotContains(r2, 'Feat')

    def test_filter_by_status_and_min_words(self):
        r = self.client.get('/novels/', {'status': 'ongoing', 'min_words': '0'})
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get('/novels/', {'status': 'bogus'})
        self.assertEqual(r2.status_code, 200)

    # --- dashboard ---
    def test_dashboard_requires_login_and_lists(self):
        self.assertEqual(self.client.get('/my/dashboard/').status_code, 302)
        self.client.force_login(self.owner)
        r = self.client.get('/my/dashboard/')
        self.assertContains(r, 'Feat')

    # --- outline ---
    def test_outline_create_and_list(self):
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{self.novel.pk}/outline/new/', {'title': 'Act 1'})
        r = self.client.get(f'/my/novels/{self.novel.pk}/outline/')
        self.assertContains(r, 'Act 1')

    def test_outline_non_owner_forbidden(self):
        self.client.force_login(self.other)
        r = self.client.get(f'/my/novels/{self.novel.pk}/outline/')
        self.assertEqual(r.status_code, 403)

    # --- volume ---
    def test_volume_create(self):
        from novels.models import Volume
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{self.novel.pk}/volumes/new/', {'title': 'Book One'})
        self.assertTrue(Volume.objects.filter(novel=self.novel, title='Book One').exists())

    # --- chapter draft toggle ---
    def test_chapter_draft_toggle_hides_from_guest(self):
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{self.novel.pk}/chapters/{self.chapter.pk}/toggle-draft/')
        self.chapter.refresh_from_db()
        self.assertTrue(self.chapter.is_draft)
        # guest cannot read a draft chapter
        self.client.logout()
        r = self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.assertEqual(r.status_code, 404)

    def test_chapter_draft_toggle_non_owner_forbidden(self):
        self.client.force_login(self.other)
        r = self.client.post(
            f'/my/novels/{self.novel.pk}/chapters/{self.chapter.pk}/toggle-draft/')
        self.assertEqual(r.status_code, 403)

    # --- report ---
    def test_report_create(self):
        from interaction.models import Report
        self.client.force_login(self.other)
        self.client.post(f'/novels/{self.novel.pk}/report/', {'reason': 'spam'})
        self.assertTrue(Report.objects.filter(novel=self.novel, reason='spam').exists())
        r = self.client.get(f'/novels/{self.novel.pk}/')
        self.assertEqual(r.status_code, 200)  # report form rendered for logged-in visitor


class NewFeatureEdgeTests(TestCase):
    """Edge/branch tests for models __str__ and view guards."""

    def setUp(self):
        self.owner = _user(username='edgeowner')
        self.other = _user(username='edgeother')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.owner, self.cat, title='Edge', published=True)

    def test_model_str_methods(self):
        from novels.models import Tag, Volume
        from interaction.models import Follow, Notification, OutlineItem, Report
        tag = Tag.objects.create(name='t1')
        self.assertEqual(str(tag), 't1')
        vol = Volume.objects.create(novel=self.novel, title='V', order=1)
        self.assertIn('Vol.1', str(vol))
        n = Notification.objects.create(
            recipient=self.owner, kind='reply', message='m')
        self.assertIn('m', str(n))
        f = Follow.objects.create(follower=self.other, author=self.owner)
        self.assertIn('follows', str(f))
        rep = Report.objects.create(reporter=self.other, novel=self.novel, reason='r')
        self.assertIn('Report', str(rep))
        oi = OutlineItem.objects.create(novel=self.novel, title='O')
        self.assertEqual(str(oi), 'O')

    def test_toc_as_owner_shows_drafts_and_volumes(self):
        from novels.models import Volume
        Volume.objects.create(novel=self.novel, title='V', order=1)
        ch = NovelService.create_chapter(self.novel, title='D', content='x')
        ch.is_draft = True
        ch.save(update_fields=['is_draft'])
        self.client.force_login(self.owner)
        r = self.client.get(f'/novels/{self.novel.pk}/toc/')
        self.assertContains(r, 'D')

    def test_outline_non_owner_forbidden(self):
        self.client.force_login(self.other)
        r = self.client.post(
            f'/my/novels/{self.novel.pk}/outline/new/', {'title': 'x'})
        self.assertEqual(r.status_code, 403)

    def test_outline_blank_title_noop(self):
        from interaction.models import OutlineItem
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{self.novel.pk}/outline/new/', {'title': '  '})
        self.assertFalse(OutlineItem.objects.exists())

    def test_volume_non_owner_forbidden(self):
        self.client.force_login(self.other)
        r = self.client.post(
            f'/my/novels/{self.novel.pk}/volumes/new/', {'title': 'x'})
        self.assertEqual(r.status_code, 403)

    def test_volume_blank_title_noop(self):
        from novels.models import Volume
        self.client.force_login(self.owner)
        self.client.post(f'/my/novels/{self.novel.pk}/volumes/new/', {'title': ''})
        self.assertFalse(Volume.objects.exists())

    def test_report_blank_reason_noop(self):
        from interaction.models import Report
        self.client.force_login(self.other)
        self.client.post(f'/novels/{self.novel.pk}/report/', {'reason': '  '})
        self.assertFalse(Report.objects.exists())


class ApiJsonTests(TestCase):
    """Read-only JSON API for the catalogue."""

    def setUp(self):
        self.user = _user(username='apiuser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = _novel(self.user, self.cat, title='Api', published=True)
        NovelService.create_chapter(self.novel, title='c', content='hello world')

    def test_api_list_returns_published(self):
        r = self.client.get('/api/novels/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['results'][0]['title'], 'Api')

    def test_api_detail_includes_chapters(self):
        r = self.client.get(f'/api/novels/{self.novel.pk}/')
        data = r.json()
        self.assertEqual(data['title'], 'Api')
        self.assertEqual(data['chapters'][0]['title'], 'c')

    def test_api_detail_unpublished_404(self):
        hidden = _novel(self.user, self.cat, title='H', published=False)
        r = self.client.get(f'/api/novels/{hidden.pk}/')
        self.assertEqual(r.status_code, 404)


class ScheduledChapterTests(TestCase):
    """scheduled_at hides chapters until due (read-time evaluation)."""

    def test_future_scheduled_chapter_hidden(self):
        from django.utils import timezone
        from datetime import timedelta
        user = _user(username='scheduluser')
        cat = Category.objects.create(name='Fantasy')
        novel = _novel(user, cat, title='S', published=True)
        ch = NovelService.create_chapter(novel, title='later', content='x')
        ch.scheduled_at = timezone.now() + timedelta(days=1)
        ch.save(update_fields=['scheduled_at'])
        r = self.client.get(f'/novels/{novel.pk}/chapters/1/')
        self.assertEqual(r.status_code, 404)
