"""Behavioural tests for the accounts app.

Each test maps to a row of the S2 inventory (see TEST_COVERAGE.md).
Test names state the behaviour and the condition, not the method called.
Pre-existing i18n tests in novels/tests.py are left untouched.

Row keys used in docstrings:
  ACC-REGISTER  ACC-PROFILE  ACC-OWNERSHIP  ACC-PERMISSION  ACC-ADMIN
  ACC-AVATAR    ACC-UPDATE
"""

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Profile
from accounts.permissions import (
    AuthorOrAdminStrategy,
    CommentOwnerStrategy,
    author_or_admin,
    comment_owner,
)
from interaction.models import Comment
from novels.models import Category, Chapter, Novel


def make_user(username='alice', password='pw12345678', **extra):
    return User.objects.create_user(username=username, password=password, **extra)


class RegistrationTests(TestCase):
    """ACC-REGISTER: registration creates a usable account."""

    def test_valid_registration_creates_user_and_logs_in(self):
        # ACC-REGISTER / creation
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'newreader',
                'email': 'new@example.com',
                'password1': 'A-strong-pass-123',
                'password2': 'A-strong-pass-123',
            },
        )
        self.assertRedirects(response, '/')
        user = User.objects.get(username='newreader')
        self.assertTrue(user.check_password('A-strong-pass-123'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_sets_password_hash_not_plaintext(self):
        # ACC-REGISTER - asserts resulting DB state, not response alone
        self.client.post(
            '/accounts/register/',
            {
                'username': 'hashcheck',
                'password1': 'A-strong-pass-123',
                'password2': 'A-strong-pass-123',
            },
        )
        raw = User.objects.values_list('password', flat=True).get(username='hashcheck')
        self.assertNotEqual(raw, 'A-strong-pass-123')
        self.assertTrue(raw.startswith('pbkdf2_'))

    def test_duplicate_username_is_rejected(self):
        # ACC-REGISTER - duplicate value
        make_user(username='taken')
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'taken',
                'password1': 'A-strong-pass-123',
                'password2': 'A-strong-pass-123',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='taken').count(), 1)

    def test_password_mismatch_is_rejected(self):
        # ACC-REGISTER - validation failure
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'mismatch',
                'password1': 'A-strong-pass-123',
                'password2': 'A-different-pass-123',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='mismatch').exists())

    def test_empty_username_is_rejected(self):
        # ACC-REGISTER - empty
        response = self.client.post(
            '/accounts/register/',
            {'username': '', 'password1': 'A-strong-pass-123',
             'password2': 'A-strong-pass-123'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_cannot_grant_admin_flag(self):
        # ACC-REGISTER - mass assignment attempt via extra fields
        self.client.post(
            '/accounts/register/',
            {
                'username': 'sneaky',
                'password1': 'A-strong-pass-123',
                'password2': 'A-strong-pass-123',
                'is_staff': 'True',
                'is_superuser': 'True',
            },
        )
        user = User.objects.get(username='sneaky')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class ProfileCreationTests(TestCase):
    """ACC-PROFILE: a profile is auto-created and display name resolves."""

    def test_profile_is_created_for_each_new_user(self):
        # ACC-PROFILE - creation via post_save signal
        user = make_user(username='withprofile')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_display_name_falls_back_to_username_when_nickname_blank(self):
        # ACC-PROFILE - empty nickname
        user = make_user(username='nonick')
        self.assertEqual(user.profile.display_name, 'nonick')

    def test_display_name_uses_nickname_when_present(self):
        # ACC-PROFILE - populated nickname
        user = make_user(username='hasnick')
        user.profile.nickname = 'Story Weaver'
        user.profile.save()
        self.assertEqual(user.profile.display_name, 'Story Weaver')


class ProfileEditTests(TestCase):
    """ACC-UPDATE: editing own profile persists changes."""

    def test_owner_can_update_nickname_and_bio(self):
        # ACC-UPDATE - update flow, asserts DB state
        user = make_user(username='editor')
        self.client.force_login(user)
        response = self.client.post(
            '/accounts/profile/edit/',
            {'nickname': 'New Name', 'bio': 'Hello there'},
        )
        self.assertRedirects(response, '/accounts/profile/')
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.nickname, 'New Name')
        self.assertEqual(user.profile.bio, 'Hello there')

    def test_nickname_longer_than_50_is_rejected(self):
        # ACC-UPDATE - too long
        user = make_user(username='longnick')
        self.client.force_login(user)
        response = self.client.post(
            '/accounts/profile/edit/',
            {'nickname': 'x' * 51, 'bio': ''},
        )
        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.nickname, '')

    def test_profile_edit_requires_login(self):
        # ACC-OWNERSHIP - anonymous redirected
        response = self.client.get('/accounts/profile/edit/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


class AuthorPageTests(TestCase):
    """ACC-PROFILE: public author page shows only published novels."""

    def setUp(self):
        self.author = make_user(username='writer')
        self.cat = Category.objects.create(name='Fantasy')
        self.published = Novel.objects.create(
            author=self.author, category=self.cat, title='Shown', is_published=True)
        self.hidden = Novel.objects.create(
            author=self.author, category=self.cat, title='Hidden', is_published=False)

    def test_author_page_lists_only_published_novels(self):
        # ACC-PROFILE - membership filter by publication
        response = self.client.get('/accounts/users/writer/')
        self.assertContains(response, 'Shown')
        self.assertNotContains(response, 'Hidden')

    def test_missing_author_returns_404(self):
        # ACC-PROFILE - empty result set
        response = self.client.get('/accounts/users/nobody-here/')
        self.assertEqual(response.status_code, 404)


class AuthorOrAdminStrategyTests(TestCase):
    """ACC-PERMISSION / ACC-OWNERSHIP: who may edit a novel."""

    def setUp(self):
        self.owner = make_user(username='owner')
        self.other = make_user(username='other')
        self.admin = make_user(username='admin', is_staff=True)
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = Novel.objects.create(
            author=self.owner, category=self.cat, title='N')

    def test_author_may_edit_own_novel(self):
        # ACC-OWNERSHIP - owner allowed
        self.assertTrue(author_or_admin.can_edit(self.novel, self.owner))

    def test_non_owner_may_not_edit_another_novel(self):
        # ACC-OWNERSHIP - access to another user's object denied
        self.assertFalse(author_or_admin.can_edit(self.novel, self.other))

    def test_admin_may_edit_any_novel(self):
        # ACC-ADMIN - administrator override
        self.assertTrue(author_or_admin.can_edit(self.novel, self.admin))

    def test_anonymous_may_not_edit(self):
        # ACC-PERMISSION - unauthenticated
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(author_or_admin.can_edit(self.novel, AnonymousUser()))

    def test_superuser_also_counts_as_admin(self):
        # ACC-ADMIN - superuser without is_staff
        root = make_user(username='root', is_superuser=True)
        self.assertTrue(author_or_admin.can_edit(self.novel, root))


class CommentOwnerStrategyTests(TestCase):
    """ACC-PERMISSION: who may delete a comment."""

    def setUp(self):
        self.owner = make_user(username='cowner')
        self.other = make_user(username='cother')
        self.admin = make_user(username='cadmin', is_staff=True)
        cat = Category.objects.create(name='Fantasy')
        novel = Novel.objects.create(author=self.owner, category=cat, title='N')
        chapter = Chapter.objects.create(
            novel=novel, title='C', content='x', order=1)
        self.comment = Comment.objects.create(
            user=self.owner, chapter=chapter, content='hi')

    def test_comment_owner_may_delete_own_comment(self):
        # ACC-OWNERSHIP - owner allowed
        self.assertTrue(comment_owner.can_edit(self.comment, self.owner))

    def test_non_owner_may_not_delete_another_comment(self):
        # ACC-OWNERSHIP - denied
        self.assertFalse(comment_owner.can_edit(self.comment, self.other))

    def test_admin_may_delete_any_comment(self):
        # ACC-ADMIN - override
        self.assertTrue(comment_owner.can_edit(self.comment, self.admin))


class ProfileModelUnitTests(TestCase):
    """accounts/models.py: Profile.__str__ (48), get_absolute_url (56-58)."""

    def test_profile_str_includes_display_name_and_username(self):
        # line 48: __str__ = '<display_name> (<username>)'
        user = make_user(username='dispuser')
        user.profile.nickname = 'Pen Name'
        user.profile.save()
        self.assertIn('Pen Name', str(user.profile))
        self.assertIn('dispuser', str(user.profile))

    def test_profile_absolute_url_targets_author_page(self):
        # lines 56-58: get_absolute_url -> accounts:author_profile
        user = make_user(username='urluser')
        self.assertEqual(
            user.profile.get_absolute_url(), '/accounts/users/urluser/')


class RegisterGetFormTests(TestCase):
    """accounts/views.py: register GET renders form (line 28)."""

    def test_register_get_renders_form(self):
        # line 28: non-POST branch builds an empty RegisterForm
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)


class RegisterAlreadyAuthenticatedTests(TestCase):
    """accounts/views.py: register redirects authenticated user (line 18)."""

    def test_authenticated_visitor_is_redirected_from_register(self):
        # line 18: is_authenticated True -> redirect home
        user = make_user(username='signedin')
        self.client.force_login(user)
        response = self.client.get('/accounts/register/')
        self.assertRedirects(response, '/')


class ProfileEditGetFormTests(TestCase):
    """accounts/views.py: edit_profile GET renders bound form (line 70)."""

    def test_owner_gets_profile_edit_form(self):
        # line 70: non-POST branch builds ProfileForm(instance=profile)
        user = make_user(username='editget')
        self.client.force_login(user)
        response = self.client.get('/accounts/profile/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].instance, user.profile)


class PermissionStrategyNonAdminTests(TestCase):
    """accounts/permissions.py: line 36/37 admin-branch false side."""

    def test_non_admin_non_owner_cannot_edit_comment(self):
        # lines 35-39: is_admin False and different user -> False
        owner = make_user(username='cowner2')
        other = make_user(username='cother2')
        cat = Category.objects.create(name='Fantasy')
        novel = Novel.objects.create(author=owner, category=cat, title='N')
        chapter = Chapter.objects.create(novel=novel, title='C', content='x', order=1)
        from interaction.models import Comment
        comment = Comment.objects.create(user=owner, chapter=chapter, content='x')
        self.assertFalse(comment_owner.can_edit(comment, other))


class CommentOwnerAnonymousTests(TestCase):
    """accounts/permissions.py: line 36 (anonymous/None) + branch 35."""

    def setUp(self):
        from interaction.models import Comment
        owner = make_user(username='aowner')
        cat = Category.objects.create(name='Fantasy')
        novel = Novel.objects.create(author=owner, category=cat, title='N')
        chapter = Chapter.objects.create(novel=novel, title='C', content='x', order=1)
        self.comment = Comment.objects.create(
            user=owner, chapter=chapter, content='x')

    def test_anonymous_user_cannot_edit_comment(self):
        # line 36: not user.is_authenticated -> False
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(comment_owner.can_edit(self.comment, AnonymousUser()))

    def test_none_user_cannot_edit_comment(self):
        # line 35 left side: user is None -> short-circuit False
        self.assertFalse(comment_owner.can_edit(self.comment, None))


class ProfileTabsAndVerifyTests(TestCase):
    """A3/D2 tabs + email verification + password reset pages."""

    def setUp(self):
        self.user = make_user(username='tabuser')
        self.cat = Category.objects.create(name='Fantasy')
        self.novel = Novel.objects.create(
            author=self.user, category=self.cat, title='Mine', is_published=True)

    def test_profile_works_tab_default(self):
        self.client.force_login(self.user)
        r = self.client.get('/accounts/profile/')
        self.assertEqual(r.context['tab'], 'works')
        self.assertContains(r, 'Mine')

    def test_profile_favorites_tab(self):
        from interaction.models import Favorite
        Favorite.objects.create(user=self.user, novel=self.novel)
        self.client.force_login(self.user)
        r = self.client.get('/accounts/profile/?tab=favorites')
        self.assertEqual(r.context['tab'], 'favorites')
        self.assertContains(r, 'Mine')

    def test_verify_email_sets_flag(self):
        self.client.force_login(self.user)
        self.client.get('/accounts/verify-email/')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.email_verified)

    def test_author_profile_shows_follow_button_for_other(self):
        other = make_user(username='viewhoer')
        self.client.force_login(other)
        r = self.client.get('/accounts/users/tabuser/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Follow')

    def test_password_reset_page_renders(self):
        r = self.client.get('/accounts/password/reset/')
        self.assertEqual(r.status_code, 200)


class VerifyEmailIdempotentTests(TestCase):
    """accounts/views.py: verify_email when already verified (branch skip)."""

    def test_verify_email_already_verified_is_idempotent(self):
        user = make_user(username='alreadyverified')
        user.profile.email_verified = True
        user.profile.save(update_fields=['email_verified'])
        self.client.force_login(user)
        response = self.client.get('/accounts/verify-email/')
        self.assertRedirects(response, '/accounts/profile/')
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
