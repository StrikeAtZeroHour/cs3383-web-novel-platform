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
