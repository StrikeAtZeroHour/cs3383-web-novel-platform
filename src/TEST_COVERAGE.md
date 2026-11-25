# Test coverage map (S2 inventory → tests)

This file links every behaviour that carries risk (the S2 inventory) to the
test(s) that pin it. Each test docstring names its row key(s).

Run the suite:
```
cd src
..\.venv\Scripts\python.exe manage.py test
```

## S2 inventory

| Module | Behaviour (row key) | Risk if untested | Edge cases | Priority |
|---|---|---|---|---|
| accounts | Registration creates a usable account (ACC-REGISTER) | broken signup, privilege escalation | duplicate username, password mismatch, empty, admin-flag injection | high |
| accounts | Profile auto-created, display name resolves (ACC-PROFILE) | missing profile crashes pages | blank nickname, populated nickname, missing author 404 | high |
| accounts | Profile update persists (ACC-UPDATE) | silent save failures | nickname >50, anonymous denied | medium |
| accounts | Author/admin may edit (ACC-PERMISSION, ACC-OWNERSHIP, ACC-ADMIN) | unauthorized edit | non-owner, anonymous, superuser | high |
| accounts | Comment owner/admin may delete (ACC-PERMISSION) | unauthorized delete | non-owner, admin | high |
| interaction | Favorite toggle add/remove (INT-FAVORITE, INT-FAVORITE-OWN) | duplicate/cannot remove | double toggle, anonymous, unpublished 404 | high |
| interaction | My favorites isolation (INT-COLLECTION) | data leak across users | empty list | high |
| interaction | Comment create binds user/chapter (INT-COMMENT) | orphan/misowned comment | empty, deleted chapter 404, ideographic | high |
| interaction | Reply one level only (INT-REPLY) | infinite nesting | reply-to-reply, missing parent | medium |
| interaction | Comment soft-delete + reply cascade (INT-COMMENT-DELETE) | resurrection/orphans | non-owner 403 | high |
| interaction | Rating 1-5 unique, update (INT-RATING) | out-of-range, duplicates | 0, 6, non-integer, unpublished 404 | medium |
| novels | Chapter numbering MAX+1 (NOV-ORDER-MAX) | order collisions | empty, consecutive, soft-deleted counts | high |
| novels | Prev/next navigation (NOV-PREVNEXT) | broken reader | first, last, inactive skipped | high |
| novels | Publish/unpublish (NOV-PUBLISH) | visibility bug | data retained on unpublish | high |
| novels | Reorder shifts siblings (NOV-CHAPTER-ORDER) | unique collision (see D-001) | clamp below 1, uniqueness | high |
| novels | Delete cascades (NOV-DELETE) | orphan rows | chapters removed | high |
| novels | Create novel sets author/unpublished (NOV-CREATE, NOV-VALIDATION) | forged author | blank title, anonymous | high |
| novels | Ownership on edit/delete/publish (NOV-PERMISSION) | unauthorized mutate | non-owner 403 each | high |
| novels | List search/filter/sort/pagination (NOV-SEARCH, NOV-FILTER, NOV-SORT, NOV-PAGINATION) | unpublished leak, paging bug | unpublished excluded, last page, empty, out-of-range | high |
| novels | Detail aggregation (NOV-AGGREGATION) | wrong rating stats | average of two ratings | medium |
| novels | Reader page content (NOV-READ, NOV-GUEST) | broken reader | inactive 404, ideographic | high |
| novels | Chapter authoring (NOV-CREATE, NOV-CHAPTER-ORDER, NOV-PERMISSION, NOV-VALIDATION) | unauthorized append | non-owner 403, empty content, reorder up | high |

## Suspected defects found by these tests

| ID | Test | Observed expectation | Likely cause |
|---|---|---|---|
| D-001 | `novels.tests.NovelServiceReorderTests.test_orders_remain_unique_after_reorder` | moving a chapter to an earlier position should not raise; instead `IntegrityError: UNIQUE constraint failed` | `NovelService.reorder_chapter` shifts siblings with one bulk `UPDATE order=F('order')+1`, which transiently collides with the `UNIQUE(novel, order)` constraint. The two-phase parking only protects the moved row, not the siblings. Test carries `@expectedFailure` so it flips to an alert when fixed. |
