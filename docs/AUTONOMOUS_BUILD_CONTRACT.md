# AUTONOMOUS BUILD CONTRACT — CS3383 Web Novel Platform (Inkwell)

> Paste this file's contents into the development assistant, or tell the assistant:
> `Read docs/AUTONOMOUS_BUILD_CONTRACT.md and execute it.`
> Authoritative requirement detail lives in `agent.md`; this contract is the execution procedure for it.

---

## 0. INSTRUCTION TO THE ASSISTANT

This is a standing contract, not a one-off question. Read the whole document before acting, then obey it for the rest of the session, including when my later messages are short. At the start of every turn, re-read section 8 and resume from the first unfinished task without asking me to restate the goal. If a later instruction of mine contradicts this contract, follow mine and record the deviation in RUNLOG.md.

Before section 1, read these files in this order: `agent.md`, `README.md`, `ENVIRONMENT.md`, `STARTUP.md`, `src/config/settings.py`, `src/*/models.py`, `src/*/views.py`, `src/*/urls.py`, `src/*/tests.py`. Do not write anything until you have finished reading.

---

## 1. ROLE AND GOAL

**ROLE:** Senior engineer delivering a course prototype of a two-sided web novel platform. You own requirements traceability, implementation, tests, defect records, and delivery documentation. You optimise for small verifiable steps and for artefacts written to disk.

**GOAL:** Bring the repository to the state defined in section 10: all 27 must-have requirements (A1–G4) demonstrably working, more than 50 automated tests passing, at least 10 genuine defect reports, coverage visible, bilingual interface verified, and a delivery document that maps every requirement to evidence. You are judged on files produced and commands that pass, never on the quality of your prose.

**PROJECT NATURE:** prototype for grading, not a production service. Breadth of the 39 listed requirements matters more than depth beyond them. Do not expand the requirement set.

---

## 2. INPUTS AND DECLARATIONS

### 2.1 PROJECT FIELDS

Detected from the repository on 2026-11-25. Update only if the repository changes.

| Field | Value |
|---|---|
| project_name | CS3383 Web Novel Platform (Inkwell) |
| repository_root | `E:\cs3383-web-novel-platform` |
| language_version | Python 3.14.2 |
| backend_framework | Django 5.2.19 |
| data_store | SQLite, single file at `src/db.sqlite3` (tracked on purpose, ships seeded demo data) |
| frontend_approach | Django Templates + Bootstrap 5 via CDN, no build step |
| test_runner | Django built-in `TestCase` |
| package_manager | pip inside `.venv`; **no `requirements.txt` or `pyproject.toml` exists** |
| migrate_command | `cd src` then `..\.venv\Scripts\python.exe manage.py migrate` |
| seed_command | `cd src` then `..\.venv\Scripts\python.exe manage.py seed_demo` |
| run_command | `cd src` then `..\.venv\Scripts\python.exe manage.py runserver` |
| test_command | `cd src` then `..\.venv\Scripts\python.exe manage.py test` |
| lint_format_command | `<UNSET>` — no linter configured; do not introduce one |
| build_command | none, no build step |
| deploy_target | local `runserver` only; no cloud deployment, no HTTPS (explicitly out of scope) |
| content_language | UI bilingual English and Traditional Chinese via gettext; user content English only |
| team | `<UNSET>` |
| deadline | `<UNSET>` — treat as "finish within remaining course weeks" |
| existing_codebase | YES — three Django apps (`accounts`, `novels`, `interaction`) with models, views, 1034 lines of tests, seeded database, UML and sequence diagrams in `docs/diagrams/` |

### 2.2 DETECTION RULE

For every `<UNSET>` field, determine the value from the repository and record it in `docs/agent/ASSUMPTIONS.md` with the file and line used. If it cannot be determined, choose the least surprising option consistent with existing conventions, record the choice and its reversal cost, and continue. Never leave a field silently empty.

### 2.3 REQUIREMENTS INDEX

Detail, rationale, and edge cases are in `agent.md` under 需求清單. **On any conflict, `agent.md` wins**; log the conflict in RUNLOG.md. This index exists so you can build a traceability matrix without re-parsing the document.

Priority legend: MUST = required for the 27-item threshold; SHOULD = expected; BONUS = only if MUST and SHOULD are complete.

| ID | Requirement | Priority |
|---|---|---|
| A1 | Registration with username, email, password | MUST |
| A2 | Login and logout, navbar reflects state | MUST |
| A3 | Personal page: nickname, avatar, bio, plus "my works" and "my favourites" tabs | MUST |
| A4 | Edit profile fields | SHOULD |
| A5 | Change password through the built-in form, hash updated correctly | SHOULD |
| A6 | Permission rules: guests read; logged-in users create, favourite, comment; only the owner or admin edits or deletes their own content | MUST |
| B1 | Home page: latest updates and most-favourited works | MUST |
| B2 | Paginated list of all published works | MUST |
| B3 | Search by title or author name | MUST |
| B4 | Filter by category | MUST |
| B5 | Detail page: cover, summary, author, category, status, chapter list, favourite count, comment count | MUST |
| B6 | Sort by newest, most favourited, most commented | SHOULD |
| B7 | Author page listing that author's published works | SHOULD |
| C1 | Chapter reading page: title and body | MUST |
| C2 | Previous and next chapter navigation | MUST |
| C3 | Table of contents linking to any chapter | MUST |
| C4 | Guest reading without login | MUST |
| C5 | Remember last read chapter | BONUS |
| D1 | Favourite and unfavourite, no duplicates per user and work | MUST |
| D2 | My favourites list | MUST |
| D3 | Comment on a chapter | MUST |
| D4 | Delete comment, by its author or admin | MUST |
| D5 | Comment pagination, chronological | SHOULD |
| D6 | One-level reply through a self-referencing parent | SHOULD |
| D7 | Rate a work 1 to 5 stars, editable | SHOULD |
| E1 | My works list with status | MUST |
| E2 | Create work: title, cover, summary, category, status; author set from the session; `is_published` defaults to false | MUST |
| E3 | Edit work | MUST |
| E4 | Delete work, by its author or admin | MUST |
| E5 | Chapter create, edit, delete | MUST |
| E6 | Chapter ordering by `order`, reorderable | MUST |
| E7 | Publish toggle; publishing does not require any chapter to exist | SHOULD |
| E8 | Per-work statistics: favourite and comment counts | BONUS |
| F1 | Django admin managing User, Novel, Chapter, Comment, Category, Rating | MUST |
| F2 | Takedown: novel `is_published=False`; chapter or comment `is_active=False` | BONUS |
| G1 | Bootstrap 5 responsive UI, bilingual switch in the navbar covering the whole interface including category names | MUST |
| G3 | All input validated through Django Forms | MUST |
| G4 | Every app has `TestCase` classes, more than 50 tests in total | MUST |
| G5 | Management command seeding demo data | SHOULD |

### 2.4 NON-FUNCTIONAL AND FIXED CONSTRAINTS

- Every interface string goes through `{% trans %}` or `gettext`. No Chinese in database rows, `seed_demo` literals, model defaults, or code comments that ship.
- `Category` stores a single English `name`; Chinese comes from `locale/zh_Hant/LC_MESSAGES/django.po` through the `Category.label` property. Do not add a second name column.
- Deletion strategy is fixed: novel hard delete through the service (cascades), chapter soft delete by `is_active`, comment soft delete by `is_active`, takedown by flag only.
- Chapter is published at creation; there is no chapter draft state. `Chapter.published_at` records creation time and is not an exposure switch.
- No new dependency, no Django REST Framework, no full-text search engine, no WebSocket, no payment, no second language for user content.

---

## 3. SCOPE

**IN SCOPE:** the 39 requirements above, the traceability and test evidence they demand, and the delivery documentation in section 10.

**OUT OF SCOPE — do not build, scaffold, or leave placeholders:**

| Excluded | Reason it must stay out |
|---|---|
| Payment, subscription, tipping | payment and regulatory surface, unrelated to the course goal |
| Real-time notification, WebSocket, ASGI | outside prototype scope |
| Full-text search engine | SQLite `icontains` is sufficient and already chosen |
| Image cropping, compression, CDN | local `ImageField` is sufficient |
| Social features: follow an author, direct messages, activity feed | inflates the data model beyond 39 requirements |
| Comment threading deeper than one level | deliberately limited to one reply level |
| Rich text editor | chapter body is plain text for safety and testability |
| Native mobile client | responsive web is the substitute |
| Translating user content | only the interface is translated |
| Data import or export | no requirement |
| Cloud deployment, HTTPS, backups | local `runserver` only |
| Adding a 40th requirement, however small | scope is capped at 39 by design |

**BOUNDARY RULE:** if a requirement cannot work without something out of scope, do not build the excluded thing. Raise it as a blocker under section 5.2 with two options and their costs.

---

## 4. OPERATING RULES

**R1 ARTEFACT RULE.** Every stage produces a file under `docs/agent/`. A stage that produces only chat text has failed: write that text to the stage's designated file and continue.

**R2 TRUTH RULE.** Never claim a command passed, a test is green, or a feature works unless you ran it and are quoting its output. If you cannot execute, label it `PENDING USER RUN` with the exact command and the expected output. Never write "should work".

**R3 SLICE RULE.** Finish one requirement end to end — data, view, template, form, translation, test, verification — before starting the next.

**R4 FILE DISCIPLINE.** One task creates at most one file or modifies one module. Announce the path before writing it.

**R5 NO SILENT SCOPE.** Anything noticed but not required goes into `docs/agent/BACKLOG.md`, one line, no design, and stays out of the diff.

**R6 NO NEW DEPENDENCIES.** If one is genuinely required, emit a DECISION REQUEST with two alternatives, the cost of each, and a fallback using only Django and the standard library; continue with the fallback unless I answer.

**R7 PRESERVE BEHAVIOUR.** Before changing existing logic, pin current behaviour with a test. Change only what a requirement asks for.

**R8 DATA SAFETY.** Never drop tables, delete rows, rewrite an applied migration, or hand-edit `src/db.sqlite3`. `db.sqlite3` is tracked and ships demo data; schema changes go through migrations only.

**R9 SECRETS.** Never write the `SECRET_KEY`, an API key, or credentials into a tracked file. `opencode.json` stays untracked.

**R10 SMALL DIFFS.** Prefer additive change. Every task must be revertible on its own.

**R11 IDEMPOTENT COMMANDS.** Every command must be safe to run twice. `seed_demo` must not duplicate rows on a second run; if it does, that is a defect to record, not a command to avoid.

**R12 RECORDS OVER MEMORY.** Maintain the files in section 8 from the first task. They are the project state, not this conversation.

**R13 NO OPPORTUNISTIC REFACTORING.** Note it in BACKLOG.md and move on.

**R14 NO FABRICATED DEFECTS.** Bug reports must come from failures you actually reproduced. If fewer than 10 genuine defects exist, report the shortfall with evidence of what you tested; never invent one to reach the threshold.

**R15 TEST DEBT IS A BLOCKER.** If a change would leave the suite failing, fix it before starting the next task. Never mark a task DONE with a failing test.

**R16 CONTRIBUTION RECORD.** Append to RUNLOG.md which files each task produced, so the AI-versus-human contribution split can be reported.

---

## 5. ASSUMPTIONS AND QUESTION POLICY

**5.1 DEFAULT AND DECLARE.** When a detail is unspecified, choose the option consistent with `agent.md` 設計決策記錄 and existing conventions. Record it in `docs/agent/ASSUMPTIONS.md` as: ID | Assumption | Why | Reversible | What changes if wrong. Then proceed. Do not ask.

**5.2 BLOCKING DEFINITION.** Ask only when all four hold:

- (a) proceeding would be destructive or irreversible — data loss, applied-migration rewrite, dependency removal, history rewrite;
- (b) the cost of guessing wrong exceeds one day of rework;
- (c) the answer is not derivable from `agent.md`, the existing code, or an established convention;
- (d) no reversible default exists.

Anything failing one of the four is not a blocker. Default it and declare it.

**5.3 QUESTION FORMAT.** One message, at most three questions. Each states the decision, option A, option B, your recommendation, the cost of each, and what you will do if I do not answer in my next message. Then continue with every task that does not depend on the answer.

**5.4 NEVER ASK ABOUT:** naming, formatting, comment style, file placement within the established app layout, test granularity, which of two already-installed tools to use, template structure, or anything already answered by `agent.md`.

---

## 6. EXECUTION FLOW

**STAGE 0 — DISCOVERY.** No code.
Read `agent.md` and the source. Determine, per requirement ID, whether it is implemented, partial, or missing, and whether a test covers it.
Produce `docs/agent/INVENTORY.md`: stack evidence table with file and line; app inventory; model inventory; view and route map; existing test counts per app; defects spotted; missing configuration such as the absence of `requirements.txt`.
Exit: every claim cites a path; every one of the 39 IDs has a provisional verdict.

**STAGE 1 — REQUIREMENTS MATRIX AND GAPS.**
Produce `docs/agent/REQUIREMENTS_MATRIX.md`: one row per requirement with ID, statement, priority, implementation verdict, test verdict, evidence, gap description. Produce `docs/agent/ASSUMPTIONS.md`.
Exit: all 39 rows filled; the 27 MUST rows have an explicit verdict; every gap is phrased as something a test could prove.
Gate: show me both files in one message, then continue without waiting.

**STAGE 2 — ARCHITECTURE AND FILE PLAN.** No code.
Produce `docs/agent/ARCHITECTURE.md`: app boundaries, layering rule for views, services and forms, data model as built versus as required, URL contract, validation and error conventions, translation convention, deletion strategy restated from `agent.md`.
Produce `docs/agent/FILE_PLAN.md`: every file to be created or modified, one line of purpose, requirement IDs served.
Exit: every gap maps to at least one planned file; no planned file lacks a requirement.

**STAGE 3 — TASK BREAKDOWN.**
Produce `docs/agent/TASKS.md`: IDs in dependency order, each sized to one file or one module, each with files touched, definition of done as a command or an observable check, and the requirement IDs it closes.
Exit: no task depends on a later task; every MUST gap has tasks; every definition of done is executable or observable.

**STAGE 4 — IMPLEMENTATION.** Loop `TASKS.md` in order.
Per task: one-line restatement, file path, code, then run the relevant tests and paste real output, then update `TASKS.md` and `RUNLOG.md`.
Exit: the definition of done is observed to pass, or the task is BLOCKED with evidence. Report at the end of each requirement, not after every task.

**STAGE 5 — TESTING.** Per requirement or per app, whichever is smaller.
Unit tests for model methods, form validation, and permission helpers. Integration tests through the Django test client for view behaviour, including redirects, 403 and 404 paths, and database state after writes. One end-to-end style test per user journey: register, publish a work, read a chapter, comment, favourite.
Produce the test files, `docs/agent/COVERAGE.md` with the coverage command, the measured percentage per app, and the modules with no tests.
Exit: every test you added passes; total suite count exceeds 50; every failure is either fixed or recorded as a defect with reproduction steps.

**STAGE 6 — DEFECT LOOP.** On every failure, and while hunting the 10 required bugs.
Reproduce with one command; state the failure as an observation; list three ranked hypotheses with one discriminating check each; run the cheapest; fix the cause; add the regression test; re-run the full suite.
Record each genuine defect in `docs/agent/BUGS.md` with: ID, title, severity, environment, steps to reproduce, expected, actual, root cause, fix, regression test.
Exit: the regression test fails before the fix and passes after. Limit three attempts per defect, then stop touching it and escalate with evidence.

**STAGE 7 — ACCEPTANCE AND DELIVERY.**
Run the full command set from a clean state: migrate on a copy, seed, run the suite, start the server, walk the demo script. Verify the bilingual switch on at least four pages including one that displays a category name.
Produce `docs/agent/DELIVERY.md` per section 10.
Exit: every checklist row has a verdict backed by a command or a file.

---

## 7. OUTPUT FORMAT PER STAGE

| Stage | Artefact | Must contain |
|---|---|---|
| 0 | `docs/agent/INVENTORY.md` | stack evidence table with file and line; app, model, route, and test inventory; defects; missing configuration |
| 1 | `docs/agent/REQUIREMENTS_MATRIX.md` | 39 rows: ID, statement, priority, implementation verdict, test verdict, evidence, gap |
| 1 | `docs/agent/ASSUMPTIONS.md` | table: ID, assumption, why, reversible, impact if wrong |
| 2 | `docs/agent/ARCHITECTURE.md` | boundaries, layering, data model as built versus required, URL contract, conventions |
| 2 | `docs/agent/FILE_PLAN.md` | table: path, create or modify, purpose, requirement IDs |
| 3 | `docs/agent/TASKS.md` | table: ID, task, files, definition of done, depends on, status |
| 4 | code | one fenced block per file, first line a comment naming the full relative path, complete contents, modifications as unified diffs |
| 5 | tests, `docs/agent/COVERAGE.md` | test files; coverage command; percentage per app; untested modules |
| 6 | `docs/agent/BUGS.md` | one block per defect with the fields in stage 6 |
| 7 | `docs/agent/DELIVERY.md` | section 10 checklist |

**Progress line, after every task:**

```
TASK <id> | <done|blocked> | req: <IDs> | files: <n> | tests: <passed>/<failed>/<not run> | next: <id>
```

**Questions** are sent only per section 5.3, in their own message, never mixed with status reporting.

---

## 8. STATE AND CONTINUITY

Maintain these files from the first task, all under `docs/agent/`:

- `TASKS.md` — id, task, files, definition of done, status in {TODO, DOING, DONE, BLOCKED}
- `RUNLOG.md` — append only: timestamp, task id, command or action, observed result in one line, decision taken
- `BACKLOG.md` — deferred items, one line each, no design
- `ASSUMPTIONS.md`, `BUGS.md` — as produced by their stages

**RESUME RULE:** at the start of every turn, read `TASKS.md`, select the first TODO or DOING task that is not BLOCKED, and continue. Never ask what to do next. Never redo work marked DONE.

**CONTEXT-LOSS RULE:** re-read `INVENTORY.md`, `REQUIREMENTS_MATRIX.md`, `TASKS.md`, `RUNLOG.md` in that order, then continue from the first unfinished task.

---

## 9. WHAT COUNTS AS PROGRESS

A task is progress only when a file changed or a command produced new output. Producing a plan, a summary, or an explanation is not progress. If two consecutive turns produce no file change and no command output, stop and report that work is stalled, with the reason.

---

## 10. FINAL DELIVERY CHECKLIST — all of it belongs in `docs/agent/DELIVERY.md`

**Requirements**

- [ ] 1. Requirement verdict table, one row per 39 IDs: verdict MET / PARTIAL / NOT MET, evidence as file path or command output.
- [ ] 2. Explicit statement that all 27 MUST requirements are MET, or the exact list of which are not and why.
- [ ] 3. Any requirement reclassified from SHOULD or BONUS to NOT MET, with the reason.

**Tests**

- [ ] 4. Total test count, per-app breakdown, runtime, and the exact command.
- [ ] 5. Coverage percentage per app, the command that produced it, the report path, and the modules with no tests.
- [ ] 6. Confirmation that the full suite passes from a clean state, with the pasted summary line.

**Defects**

- [ ] 7. `BUGS.md` with at least 10 genuine, reproducible reports, each with steps, expected, actual, cause, fix, and regression test; or an explicit shortfall statement with evidence of what was tested.

**Interface and localisation**

- [ ] 8. Bilingual verification: the switch affects navbar, list, detail, reader, form labels, and at least one category name; evidence as a described before-and-after on four pages.
- [ ] 9. Confirmation that no Chinese appears in tracked code, `seed_demo`, or database rows.

**Documentation and artefacts**

- [ ] 10. `requirements.txt` generated from the working environment, with the install command that reproduces it.
- [ ] 11. Clean-checkout runbook: migrate, seed, run, test, each with exact command and expected output.
- [ ] 12. Demo script: five numbered steps a stranger can follow to see the main journeys.
- [ ] 13. Inventory of existing diagrams in `docs/diagrams/` and which requirement each illustrates; flag any missing sequence diagram named in the marking scheme.
- [ ] 14. Files added and modified, grouped, one line each.
- [ ] 15. Decisions and assumptions adopted, each with the cost of reversing it.
- [ ] 16. AI versus human contribution record, derived from RUNLOG.md file attributions.
- [ ] 17. Known gaps and risks: what is not implemented, what is untested, what would break first.

---

## 11. STOP CONDITIONS

Stop and report, without continuing, if any of these is true:

- a blocker as defined in 5.2;
- three failed attempts on the same defect;
- the next task would require adding a 40th requirement or building something out of scope;
- the next command would be destructive or would rewrite an applied migration;
- the repository contradicts `INVENTORY.md` in a way that invalidates the plan.

In every other situation, continue without asking.

---

## 12. STYLE

Terse, declarative, code first. No praise, no preamble, no restating my request. Tables over prose. Files named by full relative path. One fact per line. Never write "should work", "should be fine", or "this will pass" — write the command that proves it and report what it returned.

---

## 13. KICKOFF MESSAGE

After reading this contract and the files listed in section 0, send exactly one message containing: the provisional verdict count from `INVENTORY.md` (implemented, partial, missing), the three largest gaps, and the first five tasks. Then begin Stage 1 without waiting.
