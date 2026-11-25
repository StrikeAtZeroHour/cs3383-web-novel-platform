# Bug Reports

Format per report: ID, title, severity, area, environment, preconditions, steps to reproduce, expected, actual, root cause, fix, verification, status. All bugs below were found and fixed in this repository; each cites the file where it lived.

| ID | Title | Severity | Area | Status |
|---|---|---|---|---|
| BUG-001 | Reordering a chapter to an earlier position raises UNIQUE IntegrityError | High | novels/service | Fixed |
| BUG-002 | Chinese UI fails to render after fresh checkout | Medium | i18n / setup | Fixed (tooling) |
| BUG-003 | `verify_email` crashes with `'bool' object is not callable` | High | accounts/view | Fixed |
| BUG-004 | Dark-mode muted text below WCAG 4.5:1 | Medium | UI / CSS | Fixed |
| BUG-005 | Status badge invisible in dark mode (`text-bg-dark`) | Medium | UI / template | Fixed |
| BUG-006 | Home 4-up novel grid inside 8-col column shrinks covers illegibly | Medium | UI / layout | Fixed |
| BUG-007 | Reader body line-height 1.9 exceeds 1.6–1.8 reading spec | Low | UI / CSS | Fixed |
| BUG-008 | Reader font can shrink below 16px on mobile | Medium | UI / JS | Fixed |
| BUG-009 | Comment like/delete touch targets < 44px | Medium | UI / a11y | Fixed |
| BUG-010 | `my_novels` and `my_favorites` rendered every row (no pagination) | Low | novels/interaction | Fixed |
| BUG-011 | Category label untranslated if `.mo` not compiled | Low | i18n | Known behaviour / documented |
| BUG-012 | Reader toolbar overlaps sticky navbar on scroll | Low | UI / layout | Fixed |

---

## BUG-001 — Reordering a chapter to an earlier position raises UNIQUE IntegrityError

- **Severity:** High
- **Area:** `src/novels/services.py` `NovelService.reorder_chapter`
- **Environment:** Django 5.2.19, SQLite, any browser
- **Preconditions:** A novel with chapters at order 1, 2, 3.
- **Steps:**
  1. Log in as the novel's author.
  2. Open the novel detail page.
  3. Press ↑ on chapter 3 to move it to position 1 (or call `reorder_chapter(chapter, 1)`).
- **Expected:** Chapter 3 moves to order 1; chapters shift; no error.
- **Actual:** `sqlite3.IntegrityError: UNIQUE constraint failed: novels_chapter.novel_id, novels_chapter.order`.
- **Root cause:** The sibling shift used one bulk `UPDATE novels_chapter SET order = order + 1` over `order >= 1 AND order < 3`. Under `UNIQUE(novel, order)`, shifting A(1→2) collides with B still at 2 mid-statement. The two-phase "park the moved row" only protected the moved row, not the siblings.
- **Fix:** Shift siblings one row at a time in an order where the destination is already vacated (descending for move-down, ascending for move-up), after parking the moved chapter outside the used range.
- **Verification:** `test_orders_remain_unique_after_reorder` (was `@expectedFailure`, now a normal passing regression test) + `test_reorder_to_same_position_is_noop`.
- **Status:** Fixed.

## BUG-002 — Chinese UI fails to render after fresh checkout

- **Severity:** Medium
- **Area:** i18n / environment (`locale/zh_Hant/LC_MESSAGES/`, `.mo` not in VCS)
- **Preconditions:** Fresh clone; `django.mo` absent (gitignored); GNU gettext `msgfmt` not installed.
- **Steps:** Switch language to Traditional Chinese in the navbar.
- **Expected:** UI strings and category labels show Chinese.
- **Actual:** All text stays English; 4 i18n tests fail (`'Fantasy' != '奇幻'`).
- **Root cause:** Translations are compiled into `django.mo`, which is not committed; `manage.py compilemessages` requires the external `msgfmt` binary, absent on this machine.
- **Fix:** Added `src/tools/compile_po.py` (stdlib `.po→.mo` compiler) and documented `compilemessages` in the runbook; also the CI workflow compiles the catalogue.
- **Verification:** `python -m tools.compile_po locale/zh_Hant/LC_MESSAGES/django.po`; the 4 i18n tests pass.
- **Status:** Fixed (tooling workaround); proper fix is installing gettext.

## BUG-003 — `verify_email` crashes with `'bool' object is not callable`

- **Severity:** High
- **Area:** `src/accounts/views.py`
- **Steps:** As a logged-in user, GET `/accounts/verify-email/`.
- **Expected:** Email marked verified, redirect to profile.
- **Actual:** `TypeError: 'bool' object is not callable` at `messages.success(request, _('Email verified.'))`.
- **Root cause:** `profile, _ = Profile.objects.get_or_create(...)` rebinds the local name `_` (the gettext alias) to the unused "created" boolean, shadowing the translation function for the rest of the function.
- **Fix:** Rename the throwaway to `_created`.
- **Verification:** `test_verify_email_sets_flag`, `test_verify_email_already_verified_is_idempotent`.
- **Status:** Fixed.

## BUG-004 — Dark-mode muted text below WCAG 4.5:1

- **Severity:** Medium
- **Area:** `src/static/css/site.css` `--muted` (dark theme)
- **Steps:** Enable dark mode; read author/count metadata on any card.
- **Expected:** Body text contrast ≥ 4.5:1.
- **Actual:** `#9aa0a6` on `#1d2126` ≈ 3.6:1.
- **Fix:** Dark `--muted` → `#b6bcc4` (8.46:1 measured). Light `--muted` also darkened to `#5b6470` (6.00:1 on white). Hero lead text moved to `--ink`.
- **Verification:** Puppeteer probe: light meta 6.00:1, dark meta 8.46:1.
- **Status:** Fixed.

## BUG-005 — Status badge invisible in dark mode

- **Severity:** Medium
- **Area:** `src/templates/novels/_novel_grid.html`
- **Steps:** Dark mode; view novel cards.
- **Expected:** "Ongoing" badge readable.
- **Actual:** `text-bg-dark` (#212529) blends into dark surface (#1d2126).
- **Fix:** Token badges `.status-ongoing` (`--accent`) / `.status-completed` (#2f6f4f).
- **Verification:** Rendered HTML contains `status-ongoing`; badge bg differs from surface.
- **Status:** Fixed.

## BUG-006 — Home 4-up grid inside 8-col column shrinks covers

- **Severity:** Medium
- **Area:** `src/templates/novels/home.html` + `_novel_grid.html`
- **Steps:** Open home at ≥1024px; observe card grid in the main column.
- **Expected:** Legible cover size.
- **Actual:** `row-cols-lg-4` inside `col-lg-8` yields ~150px cards; cover text/badges crowded.
- **Fix:** Home passes `cols="row-cols-2 row-cols-md-2 row-cols-lg-2"`; card width ~356px at 1280.
- **Verification:** Puppeteer: cardWidth=356 @1280, overlap=false.
- **Status:** Fixed.

## BUG-007 — Reader line-height exceeds spec

- **Severity:** Low
- **Area:** `src/static/css/site.css` `--reader-line`
- **Actual:** 1.9 (spec 1.6–1.8). **Fix:** 1.75. **Verification:** computed line-height 29.75px / 17px = 1.75.
- **Status:** Fixed.

## BUG-008 — Reader font shrinks below 16px on mobile

- **Severity:** Medium
- **Area:** `src/templates/novels/chapter_read.html` (JS clamp)
- **Steps:** Reader page; press A− repeatedly.
- **Actual:** Min 0.85rem = 13.6px. **Fix:** clamp min 1.0rem = 16px.
- **Verification:** A− ×8 → computed font-size ≥ 16px.
- **Status:** Fixed.

## BUG-009 — Comment like/delete touch targets < 44px

- **Severity:** Medium
- **Area:** `src/templates/novels/chapter_read.html`
- **Actual:** `btn-link p-0` text-only buttons ~16px tall. **Fix:** `btn-outline-* tap` (min 44×44).
- **Verification:** `.tap { min-width:44px; min-height:44px }`; button box ≥44px at 375.
- **Status:** Fixed.

## BUG-010 — Unbounded lists on my_novels / my_favorites

- **Severity:** Low
- **Area:** `src/novels/views.py`, `src/interaction/views.py`
- **Actual:** Returned all rows; templates iterated bare querysets. **Fix:** `Paginator` + `_pagination.html`.
- **Verification:** `test_my_novels` / favorites paginate.
- **Status:** Fixed.

## BUG-011 — Category label untranslated if `.mo` missing

- **Severity:** Low
- **Area:** i18n
- **Actual:** `Category.label` falls back to English when no compiled catalogue. **Status:** Known, documented behaviour (fallback by design); resolved by compiling messages (BUG-002 tooling).

## BUG-012 — Reader toolbar overlaps sticky navbar on scroll

- **Severity:** Low
- **Area:** `src/static/css/site.css` `.reader-toolbar`
- **Actual:** Both `position: sticky` at `top:0`. **Fix:** toolbar `top: 4.25rem` (navbar height).
- **Verification:** Puppeteer `stickyOverlap=false` at 375/768/1280.
- **Status:** Fixed.
