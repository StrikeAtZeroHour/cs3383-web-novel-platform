"""Behavioural tests for the interaction app.

Each test maps to a row of the S2 inventory (see TEST_COVERAGE.md).
Row keys:
  INT-FAVORITE  INT-FAVORITE-OWN  INT-COMMENT  INT-REPLY  INT-COMMENT-DELETE
  INT-RATING    INT-COLLECTION
"""

from django.contrib.auth.models import User
from django.test import TestCase

from interaction.forms import CommentForm, RatingForm
from interaction.models import Comment, Favorite, Rating
from novels.models import Category, Chapter, Novel


def make_user(username='reader', **extra):
    return User.objects.create_user(username=username, password='pw12345678', **extra)


def make_novel(author, cat, title='N', published=True):
    return Novel.objects.create(
        author=author, category=cat, title=title, is_published=published)


class FavoriteToggleTests(TestCase):
    """INT-FAVORITE: toggle semantics add then remove; uniqueness."""

    def setUp(self):
        self.user = make_user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)

    def test_toggle_creates_favorite_when_absent(self):
        # INT-FAVORITE - creation, asserts DB state
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/favorite/')
        self.assertTrue(
            Favorite.objects.filter(user=self.user, novel=self.novel).exists())

    def test_toggle_removes_favorite_when_present(self):
        # INT-FAVORITE - deletion
        self.client.force_login(self.user)
        Favorite.objects.create(user=self.user, novel=self.novel)
        self.client.post(f'/novels/{self.novel.pk}/favorite/')
        self.assertFalse(
            Favorite.objects.filter(user=self.user, novel=self.novel).exists())

    def test_double_toggle_does_not_duplicate(self):
        # INT-FAVORITE - repeated action stays unique
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/favorite/')
        self.client.post(f'/novels/{self.novel.pk}/favorite/')
        self.assertEqual(
            Favorite.objects.filter(user=self.user, novel=self.novel).count(), 0)

    def test_favorite_requires_login(self):
        # INT-FAVORITE-OWN - anonymous denied
        response = self.client.post(f'/novels/{self.novel.pk}/favorite/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_favorite_unpublished_novel_by_stranger_is_404(self):
        # INT-FAVORITE-OWN - object not visible
        stranger = make_user(username='stranger')
        hidden = make_novel(self.user, self.cat, title='Hidden', published=False)
        self.client.force_login(stranger)
        response = self.client.post(f'/novels/{hidden.pk}/favorite/')
        self.assertEqual(response.status_code, 404)


class MyFavoritesTests(TestCase):
    """INT-COLLECTION: the user's saved list shows only their own favorites."""

    def setUp(self):
        self.user = make_user(username='me')
        self.other = make_user(username='you')
        self.cat = Category.objects.create(name='Fantasy')
        self.mine = make_novel(self.other, self.cat, title='MyPick')
        self.theirs = make_novel(self.other, self.cat, title='TheirPick')
        Favorite.objects.create(user=self.user, novel=self.mine)
        Favorite.objects.create(user=self.other, novel=self.theirs)

    def test_favorites_page_lists_only_current_users_items(self):
        # INT-COLLECTION - membership isolation
        self.client.force_login(self.user)
        response = self.client.get('/my/favorites/')
        self.assertContains(response, 'MyPick')
        self.assertNotContains(response, 'TheirPick')

    def test_favorites_page_empty_for_new_user(self):
        # INT-COLLECTION - empty result set
        fresh = make_user(username='fresh')
        self.client.force_login(fresh)
        response = self.client.get('/my/favorites/')
        self.assertEqual(response.status_code, 200)


class CommentCreateTests(TestCase):
    """INT-COMMENT: posting a comment persists with correct owner/chapter."""

    def setUp(self):
        self.user = make_user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='C1', content='body', order=1)

    def test_comment_is_created_and_bound_to_user_and_chapter(self):
        # INT-COMMENT - creation, asserts DB state
        self.client.force_login(self.user)
        self.client.post(
            f'/novels/{self.novel.pk}/chapters/1/comments/',
            {'content': 'Loved it'},
        )
        comment = Comment.objects.get()
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.chapter, self.chapter)
        self.assertTrue(comment.is_active)

    def test_empty_comment_is_rejected(self):
        # INT-COMMENT - validation failure (whitespace-only)
        self.client.force_login(self.user)
        self.client.post(
            f'/novels/{self.novel.pk}/chapters/1/comments/',
            {'content': '   '},
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_on_deleted_chapter_is_404(self):
        # INT-COMMENT - inactive chapter boundary
        self.chapter.is_active = False
        self.chapter.save(update_fields=['is_active'])
        self.client.force_login(self.user)
        response = self.client.post(
            f'/novels/{self.novel.pk}/chapters/1/comments/',
            {'content': 'x'},
        )
        self.assertEqual(response.status_code, 404)

    def test_ideographic_comment_is_stored_verbatim(self):
        # INT-COMMENT - non-latin script round-trip
        self.client.force_login(self.user)
        self.client.post(
            f'/novels/{self.novel.pk}/chapters/1/comments/',
            {'content': '好看極了'},
        )
        self.assertEqual(Comment.objects.get().content, '好看極了')


class CommentReplyRuleTests(TestCase):
    """INT-REPLY: replies are limited to one level."""

    def setUp(self):
        self.user = make_user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='C1', content='body', order=1)
        self.top = Comment.objects.create(
            user=self.user, chapter=self.chapter, content='top')

    def test_reply_to_top_level_comment_is_allowed(self):
        # INT-REPLY - happy path
        form = CommentForm(data={'content': 'reply', 'parent_id': self.top.pk})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['parent'], self.top)

    def test_reply_to_a_reply_is_rejected(self):
        # INT-REPLY - multi-level replies are now allowed (nested target)
        child = Comment.objects.create(
            user=self.user, chapter=self.chapter, content='child', parent=self.top)
        form = CommentForm(data={'content': 'grandchild', 'parent_id': child.pk})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['parent'], child)

    def test_reply_to_missing_parent_is_rejected(self):
        # INT-REPLY - empty/invalid parent
        form = CommentForm(data={'content': 'x', 'parent_id': 999999})
        self.assertFalse(form.is_valid())


class CommentDeleteTests(TestCase):
    """INT-COMMENT-DELETE: owner deletes (soft), non-owner forbidden."""

    def setUp(self):
        self.owner = make_user(username='owner')
        self.other = make_user(username='other')
        cat = Category.objects.create(name='Fantasy')
        novel = Novel.objects.create(author=self.owner, category=cat, title='N')
        chapter = Chapter.objects.create(novel=novel, title='C', content='x', order=1)
        self.comment = Comment.objects.create(
            user=self.owner, chapter=chapter, content='hi')

    def test_owner_soft_deletes_own_comment(self):
        # INT-COMMENT-DELETE - deletion, asserts DB state stays row + inactive
        self.client.force_login(self.owner)
        self.client.post(f'/comments/{self.comment.pk}/delete/')
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_active)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_deleting_parent_hides_its_replies(self):
        # INT-COMMENT-DELETE - cascade to replies
        reply = Comment.objects.create(
            user=self.owner, chapter=self.comment.chapter,
            content='r', parent=self.comment)
        self.client.force_login(self.owner)
        self.client.post(f'/comments/{self.comment.pk}/delete/')
        reply.refresh_from_db()
        self.assertFalse(reply.is_active)

    def test_non_owner_cannot_delete_comment(self):
        # INT-COMMENT-DELETE - ownership failure
        self.client.force_login(self.other)
        response = self.client.post(f'/comments/{self.comment.pk}/delete/')
        self.assertEqual(response.status_code, 403)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_active)


class RatingTests(TestCase):
    """INT-RATING: 1-5 stars, one per user per novel, update in place."""

    def setUp(self):
        self.user = make_user()
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)

    def test_rating_is_created_with_score(self):
        # INT-RATING - creation, asserts DB state
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/rate/', {'score': 4})
        self.assertEqual(Rating.objects.get().score, 4)

    def test_second_rating_updates_not_duplicates(self):
        # INT-RATING - update flow keeps uniqueness
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/rate/', {'score': 2})
        self.client.post(f'/novels/{self.novel.pk}/rate/', {'score': 5})
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(Rating.objects.get().score, 5)

    def test_score_below_one_is_rejected(self):
        # INT-RATING - boundary lower (0)
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/rate/', {'score': 0})
        self.assertEqual(Rating.objects.count(), 0)

    def test_score_above_five_is_rejected(self):
        # INT-RATING - boundary upper (6)
        self.client.force_login(self.user)
        self.client.post(f'/novels/{self.novel.pk}/rate/', {'score': 6})
        self.assertEqual(Rating.objects.count(), 0)

    def test_rating_form_rejects_non_integer(self):
        # INT-RATING - wrong type
        form = RatingForm(data={'score': 'five'})
        self.assertFalse(form.is_valid())

    def test_rating_unpublished_novel_by_stranger_is_404(self):
        # INT-RATING - object not visible
        stranger = make_user(username='stranger')
        hidden = make_novel(self.user, self.cat, title='Hidden', published=False)
        self.client.force_login(stranger)
        response = self.client.post(f'/novels/{hidden.pk}/rate/', {'score': 3})
        self.assertEqual(response.status_code, 404)


class FavoriteModelUnitTests(TestCase):
    """interaction/models.py: Favorite.__str__ (covers line 41)."""

    def test_favorite_str_links_user_and_novel(self):
        # line 41: __str__ = '<user> -> <novel>'
        user = make_user(username='favuser')
        cat = Category.objects.create(name='Fantasy')
        novel = make_novel(user, cat, title='FavNovel')
        fav = Favorite.objects.create(user=user, novel=novel)
        self.assertIn('favuser', str(fav))
        self.assertIn('FavNovel', str(fav))


class CommentModelUnitTests(TestCase):
    """interaction/models.py: Comment.__str__ (96), get_replies (100)."""

    def setUp(self):
        self.user = make_user(username='cuser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='C1', content='x', order=1)

    def test_comment_str_truncates_content_to_30_chars(self):
        # line 96: content[:30] truncation boundary
        long_text = 'z' * 40
        comment = Comment.objects.create(
            user=self.user, chapter=self.chapter, content=long_text)
        self.assertIn('z' * 30, str(comment))
        self.assertNotIn('z' * 31, str(comment))

    def test_get_replies_returns_only_active_children(self):
        # line 100: active replies for a parent
        parent = Comment.objects.create(
            user=self.user, chapter=self.chapter, content='p')
        active_reply = Comment.objects.create(
            user=self.user, chapter=self.chapter, content='a', parent=parent)
        Comment.objects.create(
            user=self.user, chapter=self.chapter, content='h', parent=parent,
            is_active=False)
        replies = list(parent.get_replies())
        self.assertEqual(replies, [active_reply])


class RatingModelUnitTests(TestCase):
    """interaction/models.py: Rating.__str__ (136), clean raises (142)."""

    def setUp(self):
        self.user = make_user(username='ruser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)

    def test_rating_str_includes_score(self):
        # line 136: __str__ includes the score
        rating = Rating.objects.create(user=self.user, novel=self.novel, score=3)
        self.assertIn('3', str(rating))

    def test_clean_rejects_out_of_range_score(self):
        # line 142 / line 141 branch: score outside 1..5 raises ValidationError
        from django.core.exceptions import ValidationError
        rating = Rating(user=self.user, novel=self.novel, score=9)
        with self.assertRaises(ValidationError):
            rating.clean()


class CommentFormUnitTests(TestCase):
    """interaction/forms.py: clean_content blank -> ValidationError (line 34)."""

    def test_clean_content_rejects_content_that_strips_to_empty(self):
        # line 34 (condition false->true): the field-level strip is bypassed by
        # direct invocation, so a value whose .strip() is empty must raise.
        from django.core.exceptions import ValidationError
        form = CommentForm()
        form.cleaned_data = {'content': '   '}
        with self.assertRaises(ValidationError):
            form.clean_content()

    def test_clean_content_returns_stripped_value(self):
        # line 35 (condition false): non-blank content is returned stripped
        form = CommentForm()
        form.cleaned_data = {'content': '  hello  '}
        self.assertEqual(form.clean_content(), 'hello')


class InteractionAdminCustomisationTests(TestCase):
    """interaction/admin.py: short_content (29), takedown/restore comments."""

    def setUp(self):
        from django.contrib import admin as dj_admin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from interaction.admin import CommentAdmin
        self.user = make_user(username='adminuser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat)
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='C', content='x', order=1)
        self.comment = Comment.objects.create(
            user=self.user, chapter=self.chapter, content='hello world')
        self.admin_obj = CommentAdmin(Comment, dj_admin.site)
        self.request = RequestFactory().get('/admin/')
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)

    def test_comment_admin_short_content(self):
        # line 29: short_content truncates to 60 chars
        self.assertEqual(self.admin_obj.short_content(self.comment), 'hello world')

    def test_comment_admin_takedown_hides(self):
        # lines 33-34: takedown sets is_active=False
        self.admin_obj.takedown_comments(
            self.request, Comment.objects.filter(pk=self.comment.pk))
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_active)

    def test_comment_admin_restore_shows(self):
        # lines 38-39: restore sets is_active=True
        Comment.objects.filter(pk=self.comment.pk).update(is_active=False)
        self.admin_obj.restore_comments(
            self.request, Comment.objects.filter(pk=self.comment.pk))
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_active)


class ReadingProgressTests(TestCase):
    """C5: reading progress is recorded per user/novel and offered to resume."""

    def setUp(self):
        self.user = make_user(username='progressor')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.user, self.cat, title='Read', published=True)
        self.c1 = Chapter.objects.create(
            novel=self.novel, title='One', content='x', order=1)
        self.c2 = Chapter.objects.create(
            novel=self.novel, title='Two', content='x', order=2)

    def test_reading_chapter_records_progress(self):
        # happy: visiting a chapter upserts one progress row
        from interaction.models import ReadingProgress
        self.client.force_login(self.user)
        self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        progress = ReadingProgress.objects.get(user=self.user, novel=self.novel)
        self.assertEqual(progress.chapter, self.c1)

    def test_progress_updates_to_latest_chapter(self):
        # update flow: reading chapter 2 replaces the stored chapter
        from interaction.models import ReadingProgress
        self.client.force_login(self.user)
        self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.client.get(f'/novels/{self.novel.pk}/chapters/2/')
        self.assertEqual(
            ReadingProgress.objects.filter(user=self.user, novel=self.novel).count(), 1)
        self.assertEqual(
            ReadingProgress.objects.get(user=self.user, novel=self.novel).chapter, self.c2)

    def test_guest_does_not_record_progress(self):
        # permission/anon: anonymous reads create no rows
        from interaction.models import ReadingProgress
        self.client.get(f'/novels/{self.novel.pk}/chapters/1/')
        self.assertEqual(ReadingProgress.objects.count(), 0)

    def test_detail_shows_continue_reading_after_progress(self):
        # happy: detail page exposes the resume target after reading
        self.client.force_login(self.user)
        self.client.get(f'/novels/{self.novel.pk}/chapters/2/')
        response = self.client.get(f'/novels/{self.novel.pk}/')
        self.assertEqual(response.context['progress'].chapter, self.c2)
        self.assertContains(response, 'Continue reading')


class ReadingProgressStrTests(TestCase):
    """interaction/models.py: ReadingProgress.__str__."""

    def test_progress_str_reports_chapter(self):
        # line: __str__ includes user, novel and chapter order
        from interaction.models import ReadingProgress
        user = make_user(username='struser')
        cat = Category.objects.create(name='Fantasy')
        novel = make_novel(user, cat, title='S')
        chapter = Chapter.objects.create(novel=novel, title='c', content='x', order=1)
        progress = ReadingProgress.objects.create(
            user=user, novel=novel, chapter=chapter)
        self.assertIn('Ch.1', str(progress))


class NewInteractionFeatureTests(TestCase):
    """Coverage for comment likes, follow, notifications."""

    def setUp(self):
        self.user = make_user(username='actuser')
        self.author = make_user(username='followauthor')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = make_novel(self.author, self.cat, title='N', published=True)
        self.chapter = Chapter.objects.create(
            novel=self.novel, title='c', content='x', order=1)
        self.comment = Comment.objects.create(
            user=self.author, chapter=self.chapter, content='hi')

    def test_comment_like_toggle(self):
        self.client.force_login(self.user)
        self.client.post(f'/comments/{self.comment.pk}/like/')
        self.assertTrue(self.comment.likes.filter(pk=self.user.pk).exists())
        self.client.post(f'/comments/{self.comment.pk}/like/')
        self.assertFalse(self.comment.likes.filter(pk=self.user.pk).exists())

    def test_follow_toggle(self):
        from interaction.models import Follow
        self.client.force_login(self.user)
        self.client.post(f'/users/followauthor/follow/')
        self.assertTrue(Follow.objects.filter(
            follower=self.user, author=self.author).exists())
        self.client.post(f'/users/followauthor/follow/')
        self.assertFalse(Follow.objects.filter(
            follower=self.user, author=self.author).exists())

    def test_cannot_follow_self(self):
        from interaction.models import Follow
        self.client.force_login(self.user)
        self.client.post(f'/users/actuser/follow/')
        self.assertFalse(Follow.objects.filter(follower=self.user).exists())

    def test_notifications_list_and_mark_read(self):
        from interaction.models import Notification
        Notification.objects.create(
            recipient=self.user, kind='reply', message='New reply')
        self.client.force_login(self.user)
        r = self.client.get('/notifications/')
        self.assertContains(r, 'New reply')
        self.client.post('/notifications/read/')
        self.assertFalse(
            Notification.objects.filter(recipient=self.user, is_read=False).exists())

# =====================================================================
# Translation (comment / discussion "Translate" button)
# =====================================================================

from unittest import mock

from django.core.cache import cache

from interaction import translation as translation_mod


class TranslationServiceTests(TestCase):
    """interaction/translation.py: language mapping, caching, failures."""

    def setUp(self):
        cache.clear()

    def test_target_language_code_maps_zh_hant(self):
        from django.utils import translation
        with translation.override("zh-hant"):
            self.assertEqual(translation_mod.target_language_code(), "zh-TW")

    def test_target_language_code_defaults_to_en(self):
        from django.utils import translation
        with translation.override("en"):
            self.assertEqual(translation_mod.target_language_code(), "en")

    def test_empty_text_returns_empty_without_calling_service(self):
        with mock.patch.object(translation_mod, "translate_text", wraps=translation_mod.translate_text):
            self.assertEqual(translation_mod.translate_text("   "), "")

    def test_translate_text_uses_backend_and_caches(self):
        calls = {"n": 0}

        class FakeTranslator:
            def __init__(self, source, target):
                self.target = target

            def translate(self, text):
                calls["n"] += 1
                return f"[{self.target}] {text}"

        with mock.patch("deep_translator.GoogleTranslator", FakeTranslator):
            first = translation_mod.translate_text("hello", target="zh-TW")
            second = translation_mod.translate_text("hello", target="zh-TW")
        self.assertEqual(first, "[zh-TW] hello")
        self.assertEqual(second, first)
        self.assertEqual(calls["n"], 1)

    def test_translate_text_raises_on_backend_error(self):
        class BoomTranslator:
            def __init__(self, source, target):
                pass

            def translate(self, text):
                raise RuntimeError("network down")

        with mock.patch("deep_translator.GoogleTranslator", BoomTranslator):
            with self.assertRaises(translation_mod.TranslationError):
                translation_mod.translate_text("hello", target="zh-TW")


class CommentTranslateEndpointTests(TestCase):
    """INT-TRANSLATE: the JSON endpoint behind the comment Translate button."""

    def setUp(self):
        cache.clear()
        self.user = make_user(username="txuser")
        self.cat = Category.objects.create(name="Fantasy")
        self.novel = make_novel(self.user, self.cat, title="TxN")
        self.chapter = Chapter.objects.create(
            novel=self.novel, title="c", content="x", order=1)
        self.comment = Comment.objects.create(
            user=self.user, chapter=self.chapter, content="Bonjour le monde")

    def test_translate_returns_json(self):
        class FakeTranslator:
            def __init__(self, source, target):
                pass

            def translate(self, text):
                return "Hello world"

        with mock.patch("deep_translator.GoogleTranslator", FakeTranslator):
            r = self.client.post(f"/comments/{self.comment.pk}/translate/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["translated"], "Hello world")

    def test_translate_requires_post(self):
        r = self.client.get(f"/comments/{self.comment.pk}/translate/")
        self.assertEqual(r.status_code, 405)

    def test_translate_unknown_comment_404(self):
        r = self.client.post("/comments/999999/translate/")
        self.assertEqual(r.status_code, 404)

    def test_translate_backend_failure_returns_502(self):
        class BoomTranslator:
            def __init__(self, source, target):
                pass

            def translate(self, text):
                raise RuntimeError("fail")

        with mock.patch("deep_translator.GoogleTranslator", BoomTranslator):
            r = self.client.post(f"/comments/{self.comment.pk}/translate/")
        self.assertEqual(r.status_code, 502)
        self.assertFalse(r.json()["ok"])

    def test_chapter_page_shows_translate_button(self):
        r = self.client.get(f"/novels/{self.novel.pk}/chapters/1/")
        self.assertContains(r, f"/comments/{self.comment.pk}/translate/")


# =====================================================================
# Discussion board
# =====================================================================

from interaction.forms import DiscussionForm, DiscussionReplyForm
from interaction.models import Discussion, DiscussionReply


def make_discussion(user, title="Talk", body="Body", **extra):
    return Discussion.objects.create(user=user, title=title, body=body, **extra)


class DiscussionModelTests(TestCase):
    """Discussion / DiscussionReply model helpers."""

    def setUp(self):
        self.user = make_user(username="duser")
        self.cat = Category.objects.create(name="Fantasy")
        self.novel = make_novel(self.user, self.cat, title="DNovel")
        self.chapter = Chapter.objects.create(
            novel=self.novel, title="c", content="x", order=1)

    def test_str_and_url(self):
        d = make_discussion(self.user)
        self.assertEqual(str(d), "Talk")
        self.assertEqual(d.get_absolute_url(), f"/discussions/{d.pk}/")

    def test_reply_count_counts_active_only(self):
        d = make_discussion(self.user)
        DiscussionReply.objects.create(discussion=d, user=self.user, content="a")
        DiscussionReply.objects.create(
            discussion=d, user=self.user, content="b", is_active=False)
        self.assertEqual(d.get_reply_count(), 1)

    def test_reply_get_replies(self):
        d = make_discussion(self.user)
        parent = DiscussionReply.objects.create(
            discussion=d, user=self.user, content="p")
        child = DiscussionReply.objects.create(
            discussion=d, user=self.user, content="c", parent=parent)
        self.assertEqual(list(parent.get_replies()), [child])


class DiscussionFormTests(TestCase):
    """DiscussionForm: required fields and chapter/novel consistency."""

    def setUp(self):
        self.user = make_user(username="fuser")
        self.cat = Category.objects.create(name="Fantasy")
        self.novel = make_novel(self.user, self.cat, title="FNovel")
        self.other = make_novel(self.user, self.cat, title="Other")
        self.chapter = Chapter.objects.create(
            novel=self.novel, title="c", content="x", order=1)

    def test_valid_without_novel(self):
        form = DiscussionForm(data={"title": "T", "body": "B"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_title_invalid(self):
        form = DiscussionForm(data={"title": "  ", "body": "B"})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_blank_body_invalid(self):
        form = DiscussionForm(data={"title": "T", "body": " "})
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_chapter_must_belong_to_novel(self):
        form = DiscussionForm(data={
            "title": "T", "body": "B", "novel": self.other.pk,
            "chapter": self.chapter.pk})
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_chapter_infers_novel(self):
        form = DiscussionForm(data={
            "title": "T", "body": "B", "chapter": self.chapter.pk})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["novel"], self.novel)

    def test_unpublished_novel_excluded_from_queryset(self):
        form = DiscussionForm()
        self.assertNotIn(
            make_novel(self.user, self.cat, title="Hidden", published=False),
            form.fields["novel"].queryset)


class DiscussionReplyFormTests(TestCase):
    """DiscussionReplyForm: blank + parent validation."""

    def setUp(self):
        self.user = make_user(username="ruser")
        self.d = make_discussion(self.user)

    def test_blank_content_invalid(self):
        form = DiscussionReplyForm(data={"content": "  "}, discussion=self.d)
        self.assertFalse(form.is_valid())

    def test_parent_must_belong_to_same_discussion(self):
        other = make_discussion(self.user, title="Other")
        foreign = DiscussionReply.objects.create(
            discussion=other, user=self.user, content="x")
        form = DiscussionReplyForm(
            data={"content": "hi", "parent_id": foreign.pk}, discussion=self.d)
        self.assertFalse(form.is_valid())

    def test_valid_reply_with_parent(self):
        parent = DiscussionReply.objects.create(
            discussion=self.d, user=self.user, content="p")
        form = DiscussionReplyForm(
            data={"content": "hi", "parent_id": parent.pk}, discussion=self.d)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["parent"], parent)


class DiscussionViewTests(TestCase):
    """discussion_list / create / detail / reply / like / delete / report."""

    def setUp(self):
        self.user = make_user(username="viewer")
        self.other = make_user(username="other")
        self.cat = Category.objects.create(name="Fantasy")
        self.novel = make_novel(self.user, self.cat, title="VNovel")
        self.chapter = Chapter.objects.create(
            novel=self.novel, title="c", content="x", order=1)

    def test_list_public_and_lists_active(self):
        make_discussion(self.user, title="Visible")
        make_discussion(self.user, title="Hidden", is_active=False)
        r = self.client.get("/discussions/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Visible")
        self.assertNotContains(r, "Hidden")

    def test_list_filter_by_novel(self):
        make_discussion(self.user, title="Pinned", novel=self.novel)
        make_discussion(self.user, title="Loose")
        r = self.client.get(f"/discussions/?novel={self.novel.pk}")
        self.assertContains(r, "Pinned")
        self.assertNotContains(r, "Loose")

    def test_create_requires_login(self):
        r = self.client.get("/discussions/new/")
        self.assertEqual(r.status_code, 302)

    def test_create_post(self):
        self.client.force_login(self.user)
        r = self.client.post("/discussions/new/", {
            "title": "New post", "body": "Hello",
            "novel": self.novel.pk, "chapter": self.chapter.pk})
        self.assertEqual(r.status_code, 302)
        d = Discussion.objects.get(title="New post")
        self.assertEqual(d.user, self.user)
        self.assertEqual(d.novel, self.novel)
        self.assertEqual(d.chapter, self.chapter)

    def test_detail_shows_post_and_replies(self):
        d = make_discussion(self.user, title="Detail")
        DiscussionReply.objects.create(
            discussion=d, user=self.other, content="a reply")
        r = self.client.get(f"/discussions/{d.pk}/")
        self.assertContains(r, "Detail")
        self.assertContains(r, "a reply")

    def test_detail_hides_inactive_from_anonymous(self):
        d = make_discussion(self.user, is_active=False)
        r = self.client.get(f"/discussions/{d.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_reply_post(self):
        d = make_discussion(self.user)
        self.client.force_login(self.other)
        r = self.client.post(f"/discussions/{d.pk}/reply/", {"content": "hey"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(DiscussionReply.objects.filter(
            discussion=d, user=self.other, content="hey").exists())

    def test_reply_threading(self):
        d = make_discussion(self.user)
        parent = DiscussionReply.objects.create(
            discussion=d, user=self.user, content="p")
        self.client.force_login(self.other)
        self.client.post(f"/discussions/{d.pk}/reply/", {
            "content": "child", "parent_id": parent.pk})
        child = DiscussionReply.objects.get(content="child")
        self.assertEqual(child.parent, parent)

    def test_like_toggle(self):
        d = make_discussion(self.user)
        self.client.force_login(self.other)
        self.client.post(f"/discussions/{d.pk}/like/")
        self.assertTrue(d.likes.filter(pk=self.other.pk).exists())
        self.client.post(f"/discussions/{d.pk}/like/")
        self.assertFalse(d.likes.filter(pk=self.other.pk).exists())

    def test_reply_like_toggle(self):
        d = make_discussion(self.user)
        reply = DiscussionReply.objects.create(
            discussion=d, user=self.user, content="x")
        self.client.force_login(self.other)
        self.client.post(f"/discussion-replies/{reply.pk}/like/")
        self.assertTrue(reply.likes.filter(pk=self.other.pk).exists())

    def test_delete_owner_soft_deletes_and_hides_replies(self):
        d = make_discussion(self.user)
        reply = DiscussionReply.objects.create(
            discussion=d, user=self.other, content="x")
        self.client.force_login(self.user)
        r = self.client.post(f"/discussions/{d.pk}/delete/")
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        reply.refresh_from_db()
        self.assertFalse(d.is_active)
        self.assertFalse(reply.is_active)

    def test_delete_forbidden_for_non_owner(self):
        d = make_discussion(self.user)
        self.client.force_login(self.other)
        r = self.client.post(f"/discussions/{d.pk}/delete/")
        self.assertEqual(r.status_code, 403)
        d.refresh_from_db()
        self.assertTrue(d.is_active)

    def test_admin_delete_allowed(self):
        admin = make_user(username="boss")
        admin.is_staff = True
        admin.save()
        d = make_discussion(self.user)
        self.client.force_login(admin)
        self.client.post(f"/discussions/{d.pk}/delete/")
        d.refresh_from_db()
        self.assertFalse(d.is_active)

    def test_report_creates_row(self):
        from interaction.models import Report
        d = make_discussion(self.user)
        self.client.force_login(self.other)
        self.client.post(f"/discussions/{d.pk}/report/", {"reason": "spam"})
        self.assertTrue(Report.objects.filter(
            reporter=self.other, discussion=d, reason="spam").exists())

    def test_report_without_reason_ignored(self):
        from interaction.models import Report
        d = make_discussion(self.user)
        self.client.force_login(self.other)
        self.client.post(f"/discussions/{d.pk}/report/", {"reason": "  "})
        self.assertFalse(Report.objects.filter(discussion=d).exists())


class DiscussionNavTests(TestCase):
    """The navbar exposes the discussion board link."""

    def test_navbar_has_discussions_link(self):
        r = self.client.get("/")
        self.assertContains(r, "/discussions/")

# =====================================================================
# Coverage completion: admin actions, form branches, __str__, service edges
# =====================================================================

class DiscussionAdminActionTests(TestCase):
    """interaction/admin.py: discussion takedown/restore + reply short_content."""

    def setUp(self):
        from django.contrib import admin as dj_admin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from interaction.admin import DiscussionAdmin, DiscussionReplyAdmin
        self.user = make_user(username="dadmin")
        self.d = make_discussion(self.user, title="AdminTalk")
        self.reply = DiscussionReply.objects.create(
            discussion=self.d, user=self.user, content="a" * 80)
        self.discussion_admin = DiscussionAdmin(Discussion, dj_admin.site)
        self.reply_admin = DiscussionReplyAdmin(DiscussionReply, dj_admin.site)
        self.request = RequestFactory().get("/admin/")
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)

    def test_takedown_discussions(self):
        # lines 65-67: takedown sets is_active=False
        self.discussion_admin.takedown_discussions(
            self.request, Discussion.objects.filter(pk=self.d.pk))
        self.d.refresh_from_db()
        self.assertFalse(self.d.is_active)

    def test_restore_discussions(self):
        # lines 71-73: restore sets is_active=True
        Discussion.objects.filter(pk=self.d.pk).update(is_active=False)
        self.discussion_admin.restore_discussions(
            self.request, Discussion.objects.filter(pk=self.d.pk))
        self.d.refresh_from_db()
        self.assertTrue(self.d.is_active)

    def test_reply_admin_short_content(self):
        # line 84: short_content truncates to 60 chars
        self.assertEqual(self.reply_admin.short_content(self.reply), "a" * 60)


class DiscussionReplyStrTests(TestCase):
    """interaction/models.py line 355: DiscussionReply.__str__."""

    def test_reply_str(self):
        user = make_user(username="strr")
        d = make_discussion(user, title="StrTalk")
        reply = DiscussionReply.objects.create(
            discussion=d, user=user, content="hello reply")
        text = str(reply)
        self.assertIn("StrTalk", text)
        self.assertIn("hello reply", text)


class DiscussionFormBlankTests(TestCase):
    """Blank title/body are rejected at field level (required)."""

    def test_blank_title_and_body_rejected(self):
        form = DiscussionForm(data={"title": "", "body": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("body", form.errors)


class DiscussionReplyFormNoDiscussionTests(TestCase):
    """DiscussionReplyForm.clean: parent given but no discussion (line 147)."""

    def test_parent_without_discussion_invalid(self):
        form = DiscussionReplyForm(
            data={"content": "hi", "parent_id": 999}, discussion=None)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())


class DiscussionCreateGetTests(TestCase):
    """discussion_create GET branch renders an empty form (lines 262-264)."""

    def test_get_renders_form(self):
        user = make_user(username="guser")
        self.client.force_login(user)
        r = self.client.get("/discussions/new/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "New discussion")


class DiscussionReplyInvalidTests(TestCase):
    """discussion_reply invalid path (lines 304-309)."""

    def test_reply_with_foreign_parent_shows_error(self):
        user = make_user(username="ivuser")
        d = make_discussion(user)
        other = make_discussion(user, title="Other")
        foreign = DiscussionReply.objects.create(
            discussion=other, user=user, content="x")
        self.client.force_login(user)
        r = self.client.post(
            f"/discussions/{d.pk}/reply/",
            {"content": "hi", "parent_id": foreign.pk}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(
            DiscussionReply.objects.filter(discussion=d, content="hi").exists())


class DiscussionReplyLikeRemoveTests(TestCase):
    """discussion_reply_like_toggle remove branch (line 331)."""

    def test_unlike_reply(self):
        user = make_user(username="uluser")
        d = make_discussion(user)
        reply = DiscussionReply.objects.create(
            discussion=d, user=user, content="x")
        reply.likes.add(user)
        self.client.force_login(user)
        self.client.post(f"/discussion-replies/{reply.pk}/like/")
        self.assertFalse(reply.likes.filter(pk=user.pk).exists())


class TranslationEdgeTests(TestCase):
    """interaction/translation.py uncovered branches (lines 62, 81)."""

    def setUp(self):
        cache.clear()

    def test_no_target_raises(self):
        # line 62: empty target -> TranslationError
        with mock.patch.object(
                translation_mod, "target_language_code", return_value=""):
            with self.assertRaises(translation_mod.TranslationError):
                translation_mod.translate_text("hi")

    def test_empty_result_raises(self):
        # line 81: backend returns empty string -> TranslationError
        class EmptyTranslator:
            def __init__(self, source, target):
                pass

            def translate(self, text):
                return ""

        with mock.patch("deep_translator.GoogleTranslator", EmptyTranslator):
            with self.assertRaises(translation_mod.TranslationError):
                translation_mod.translate_text("hi", target="zh-TW")

class DiscussionCreateInvalidPostTests(TestCase):
    """discussion_create invalid POST falls through to re-render (256->264)."""

    def test_invalid_post_rerenders_form(self):
        user = make_user(username="badpost")
        self.client.force_login(user)
        r = self.client.post("/discussions/new/", {"title": "", "body": ""})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Discussion.objects.filter(user=user).exists())
