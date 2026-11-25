"""Seed the database with demo data (G5).

Usage:
    python manage.py seed_demo

Idempotent: safe to run repeatedly. Creates categories, an admin, two authors
with novels/chapters, favorites, comments and ratings.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext as _

from interaction.models import Comment, Favorite, Rating
from novels.models import Category, Chapter, Novel
from novels.services import NovelService

CATEGORIES = [
    # English labels; translations live in locale/zh_Hant/LC_MESSAGES/django.po
    _('Fantasy'),
    _('Science Fiction'),
    _('Mystery'),
    _('Romance'),
    _('Urban'),
    _('Historical'),
]

NOVELS = [
    {
        'title': 'The Lantern Keeper',
        'author': 'alice',
        'category': _('Fantasy'),
        'summary': 'A girl inherits a lighthouse that guides lost souls home.',
        'status': Novel.Status.ONGOING,
        'chapters': [
            ('The First Light', 'The lamp had not been lit for forty years...\n\nThe town forgot the keeper, but the sea did not.'),
            ('A Visitor From the Fog', 'At midnight a boat arrived, rowed by no one at all.'),
        ],
    },
    {
        'title': 'Signal from Ganymede',
        'author': 'alice',
        'category': _('Science Fiction'),
        'summary': 'A lone engineer receives a message that should not exist.',
        'status': Novel.Status.ONGOING,
        'chapters': [
            ('Ping', 'The console blinked once every eleven minutes. Exactly.'),
        ],
    },
    {
        'title': 'The Quiet Street',
        'author': 'bob',
        'category': _('Mystery'),
        'summary': 'Every neighbour remembers a different number of houses.',
        'status': Novel.Status.COMPLETED,
        'chapters': [
            ('Number Nine', 'There was no number nine, and yet the door was open.'),
            ('The Ledger', 'The landlord kept two lists. Only one was true.'),
            ('Last Call', 'She knocked. Someone knocked back.'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Populate the database with demo categories, users, novels and interactions.'

    @transaction.atomic
    def handle(self, *args, **options):
        for name in CATEGORIES:
            Category.objects.get_or_create(name=name)

        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin@example.com'},
        )
        if created:
            admin.set_password('admin12345')
            admin.save()
            self.stdout.write('Created admin (password: admin12345)')

        for username in ('alice', 'bob'):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password('demo12345')
                user.save()
                user.profile.nickname = username.capitalize()
                user.profile.bio = f'Hi, I am {username.capitalize()} and I write stories.'
                user.profile.save()

        for data in NOVELS:
            author = User.objects.get(username=data['author'])
            category = Category.objects.get(name=data['category'])
            novel, created = Novel.objects.get_or_create(
                title=data['title'],
                author=author,
                defaults={
                    'category': category,
                    'summary': data['summary'],
                    'status': data['status'],
                },
            )
            if not created:
                continue

            for title, content in data['chapters']:
                NovelService.create_chapter(novel, title=title, content=content)
            NovelService.publish(novel)

            first_chapter = novel.chapters.active().first()
            reviewers = User.objects.exclude(pk=author.pk)[:2]
            for reviewer in reviewers:
                Favorite.objects.get_or_create(user=reviewer, novel=novel)
                Rating.objects.get_or_create(
                    user=reviewer, novel=novel, defaults={'score': 4}
                )
                Comment.objects.get_or_create(
                    user=reviewer,
                    chapter=first_chapter,
                    parent=None,
                    content='Great opening — I want to read more!',
                )
            self.stdout.write(f'Created novel: {novel.title}')

        # A reply and a comment on another chapter, for the comment UI.
        bob = User.objects.get(username='bob')
        alice = User.objects.get(username='alice')
        lantern = Novel.objects.filter(title='The Lantern Keeper').first()
        if lantern:
            chapter = lantern.chapters.active().first()
            top = Comment.objects.filter(chapter=chapter, parent=None).first()
            if top:
                Comment.objects.get_or_create(
                    user=alice,
                    chapter=chapter,
                    parent=top,
                    content='Thank you! Chapter two is coming soon.',
                )

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
