"""Permission strategies (Strategy pattern).

See `docs/diagrams/02-class-diagram.md` and `04-sequence.md` (SD-3, SD-4, SD-5).
`User.is_admin()` is the only place that decides who is an administrator.
"""


class PermissionStrategy:
    """Abstract strategy: decide whether `user` may edit/delete an object."""

    def can_edit(self, obj, user) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class AuthorOrAdminStrategy(PermissionStrategy):
    """Author of the novel, or an administrator.

    Always receives a `Novel` instance; when checking a chapter, callers pass
    `chapter.novel`, because `Chapter` has no `author` field. Keeping the
    parameter a `Novel` removes the need for `isinstance` checks here.
    """

    def can_edit(self, novel, user) -> bool:
        if user is None or not user.is_authenticated:
            return False
        if user.is_admin():
            return True
        return novel.author_id == user.pk


class CommentOwnerStrategy(PermissionStrategy):
    """Author of the comment, or an administrator (D4)."""

    def can_edit(self, comment, user) -> bool:
        if user is None or not user.is_authenticated:
            return False
        if user.is_admin():
            return True
        return comment.user_id == user.pk


# Ready-to-use singletons.
author_or_admin = AuthorOrAdminStrategy()
comment_owner = CommentOwnerStrategy()
