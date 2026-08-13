# ORU Scheduling Engine — Project Spec

## Scope: undergraduate students only

koala v1 is scoped to undergraduate ORU students only. `students.class_standing`
uses undergraduate-only vocabulary (freshman/sophomore/junior/senior), and
graduate programs at ORU don't share undergraduate's gen-ed/Christian-
coursework core structure — they would need a genuinely different
requirement model, not a relabeled version of this one. Supporting both
was considered and deliberately deferred rather than attempted in v1.

## Onboarding data sourcing

Majors and minors are manually encoded into `programs` from ORU's real
public catalog — not scraped. The list is small (ORU has 150+ majors,
minors, and pre-professional programs total) and changes rarely, making
a one-time manual compilation more appropriate than scraper
infrastructure (fragile against site changes, no formal API, ToS
considerations for automated access to catalog pages).

- **Minors**: ORU publishes a complete, current table at
  https://oru.edu/admissions/minors.php — 41 minors with department,
  pulled directly during design (Aug 2026). Seed `programs` (type
  `'minor'`) from this table directly.
- **Majors**: no equivalent single flat list — closest source is
  individual degree plan PDFs at https://degreeplansheets.oru.edu
  (ORU's Degree Works portal). Per the original schema design decision,
  only 2-3 real majors need to be manually encoded for v1 — pick from
  this source rather than attempting to enumerate ORU's full major list.
- **Sections (class times)**: fundamentally different sourcing problem
  from majors/minors — offerings and time slots change every semester,
  and ORU's actual per-semester "Schedule of Classes" (specific section
  meeting times) sits behind a student portal login, not on the open
  web. Do NOT attempt to scrape or automate against any login-walled
  registration system — same principle as never touching real student
  records. `sections` data is hand-built synthetic data (see
  `db/seed_test_catalog.sql` for the established pattern), designed to
  behave realistically (including deliberate conflicts) without
  claiming to be ORU's actual live timetable. Course codes/titles/credit
  hours can optionally be pulled from the public catalog at
  catalog.oru.edu for authenticity — that's genuinely public, same
  category as the minors page — but section meeting times stay
  invented/representative.

Worth knowing for context (not a build requirement): ORU has already
moved to Degree Works for official degree tracking through the
registrar. koala isn't competing with or replacing it — it demonstrates
constraint-based multi-semester scheduling that Degree Works-style tools
typically don't do.

## Manual dataset import format

Hand-compiled real data (course names, programs, requirements,
prerequisites, section times) gets imported via `db/import_catalog.py`
from one CSV per table, using human-readable natural keys instead of
UUIDs. Two-phase import: resolve every natural-key reference first,
collecting all failures rather than stopping at the first one; write
nothing at all if any failures exist, otherwise write everything in one
transaction. Unmatched references, duplicates, and self-references are
all hard failures with row-level context in the error output — never a
silent skip, null FK, or fuzzy/implicit match. Same principle as the
Auth Admin API teardown hardening and the "Before User Created" hook
being preferred over the raw-trigger pattern: silent data loss on a
hand-typed catalog is worse than the script refusing to run.

- `courses.csv`: `code, title, credit_hours, offering_frequency, department`
- `programs.csv`: `name, type, department, required_by_program_name`
- `degree_requirements.csv`: `program_name, course_code, category`
- `prerequisites.csv`: `course_code, prerequisite_course_code`
- `sections.csv`: `course_code, term, section_label, days, start_time, end_time`
  — **note the `section_label` column**, added after `sections`/
  `section_meetings` were split (see "Real day/time overlap logic"
  below). Multiple CSV rows sharing the same
  `(course_code, term, section_label)` collapse into one `sections` row
  plus one `section_meetings` row per CSV row — this is how a section
  with a lecture-plus-lab split (two different day/time patterns) gets
  represented as two CSV rows under the same section_label. No seats
  column — see below.

## No seat capacity tracking

`sections` intentionally has no `seats_total`/`seats_taken` — removed via
`migration_004_remove_seat_tracking.sql`. koala has no live connection to
ORU's registration system (same principle as the login-wall boundary on
section time sourcing), so seat counts could only ever be a stale,
manually-entered snapshot displayed as if it were current. Rather than
show a number that looks live but isn't, don't show one at all. This
also means the solver has never used seat capacity as a constraint —
only time conflicts, prerequisites, tier priority, and credit bounds —
so this removal doesn't affect any solver logic, only schema and any UI
that was displaying seat counts (e.g. the override modal's section list
shows just the meeting time, not seat availability).

## Prerequisite data (v1 simplification)

Real prerequisite requirements live in ORU's course catalog PDF
(hundreds of pages, distributed per catalog year, not individually
browsable online) — verifying every prerequisite against the current
catalog year wasn't practical to do reliably for v1. Instead,
`prerequisites.csv` uses **sequence-informed inference**: prerequisite
edges derived from a real degree plan sheet's recommended semester
sequencing plus standard CS-curriculum structure (e.g. Data Structures
reasonably follows Intermediate Programming), NOT verified against
current course catalog text. This is the same honesty pattern as
synthetic `sections` data — clearly labeled as an inference, not
presented as ORU's authoritative requirement. Fine for demonstrating the
solver's prerequisite-pruning and DFS cycle-detection logic, which is
the actual point; would need real catalog verification before this
could be presented as accurate to a real student.

## What this is

A degree-audit and constraint-based schedule optimizer for Oral Roberts
University students. Given a student's declared major(s)/minor(s), class
standing, and course history, the engine recommends an optimal multi-semester
course schedule that satisfies all degree requirements while respecting
section time conflicts, prerequisite chains, and credit-hour bounds — and
projects an expected graduation date that updates live as the student edits
their plan.

**This is not machine learning.** The recommendation engine is a constraint
satisfaction / backtracking solver with a priority-scoring heuristic. Refer
to it as "the engine," "the solver," or "the recommendation engine" — never
"AI" — since there is no trained model involved, and calling it AI creates
an indefensible claim in interviews.

**Data note:** this project runs on synthetic/mock student data and manually
encoded ORU course catalog data (public/catalog-level info only). It does
not connect to ORU's real student information system — that would require
FERPA-governed institutional data agreements outside the scope of a student
portfolio project. Any README or demo should say this explicitly.

---

## Tech stack (locked)

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python) |
| Backend packaging | Docker |
| Backend hosting | Render (free tier) |
| Database | PostgreSQL via Supabase |
| Auth | Supabase Auth (email/magic link) |
| Caching | Redis (computed schedule caching) |
| Frontend | React + TypeScript |
| CI/CD | GitHub Actions |
| Testing | pytest (backend), same pattern as prior food-bank project — aim for a real test suite, not token coverage |

Local dev should mirror prod: `docker-compose.yml` running the FastAPI app +
Redis as containers, pointing at a Supabase project for Postgres/Auth (no
local Postgres container needed since Supabase is already managed/hosted).

---

## Product flow

### 1. Landing page
Interactive marketing/info page. Includes a reviews/ratings section
(seed with clearly-labeled synthetic reviews if no real users yet — do not
present mock reviews as real).

### 2. Auth
- Sign in / create account via Supabase Auth.
- Signup fields: first name, last name, school (v1: hardcode to ORU or a
  small dropdown of schools actually modeled — do NOT use free-text school
  input, since the whole value of this tool depends on real, encoded degree
  requirements per school).
- Password + confirm handled by Supabase Auth SDK directly — do not
  hand-roll password hashing/storage.
- Email verification code flow via Supabase Auth.
- On verification success, redirect seamlessly into onboarding.

### 3. Onboarding
1. Select major(s) and minor(s) — multi-select, supports double majors and
   multiple minors.
2. Confirm class standing (freshman/sophomore/junior/senior) and current
   term (fall/spring).
3. Confirm course history: show ALL courses (not filtered by class
   standing — some students are ahead of pace), tag each as `done` /
   `in_progress` / `not_taken`. Untaken courses dim in the UI (UI-only
   concern, not a data filter). A course confirmed once satisfies every
   program requirement it applies to — do not ask the student to confirm
   the same course separately per major/minor.
4. Brief dismissible tutorial overlay (not a separate page) walking through
   main workpage features. Persist completion via
   `students.has_completed_tutorial`, not client-side storage.
5. Engine generates the first recommended schedule.

### 4. Main workpage
Primary interaction is NOT manual course picking — the engine recommends a
full schedule; the student can override individual choices. Manual-only
selection would be no better than existing registration tools, and defeats
the point of the project (see "Priority system" and "Re-solve cascade"
below for what happens on an override).

Must show:
- Current recommended/committed schedule (calendar or list view — TBD in
  frontend design pass)
- Credit hours: taken / in progress / remaining
- Projected graduation month/year, and how it changes live on edits
- Multi-semester outlook (future semesters under the current plan)
- Flagged (poor-choice) semesters/courses with a visible indicator and
  `flag_reason`
- Cost delta for extending graduation (v1: simple credit-hours × rate
  calculation — do not over-invest here, it's a minor feature)

### Deferred features (explicitly out of v1 scope)
- Transfer credit from Sofia Learning / community colleges — stub with a
  small hardcoded equivalency table if needed for demo purposes; do not
  build real equivalency data ingestion.
- Department-facing analytics ("students prefer this section moved to
  evenings") — build on synthetic/generated usage data only, clearly
  labeled as illustrative, not real institutional data.
- Multi-scenario "what-if" planning (see below).
- Lookahead tiebreaking (see below).

---

## Priority system

When the solver must choose between competing courses for the same
requirement or time slot, it uses a tiered priority, highest first:

1. **Structurally-required minors** — a minor mandated by a major (e.g. CS
   requires a Math minor) is promoted to Tier 1, same weight as a major.
   Modeled via `programs.required_by_program_id`.
2. **Declared majors** — including any Tier-1-promoted minor. Multiple
   majors default to equal priority (v1). `student_programs.priority_rank`
   exists for a student to optionally rank them, but is not required.
3. **Elective/free-standing minors** — not required by any declared major.
4. **Gen-eds** — includes ORU's Christian coursework requirements; these
   aren't a separate category in the schema, they're part of the gen-ed
   core (`degree_requirements.category = 'gen_ed'` covers both).

### Bottleneck score (tiebreaker within a tier)

```
score = frequency_weight(offering_frequency) + (unlocks_count * 5)

frequency_weight:
  biennial          -> 100
  annual            -> 50
  every_semester    -> 0
```

`unlocks_count` = how many other remaining required courses list this
course as a prerequisite (dependency-graph out-degree). Rare-offering
courses dominate the score because missing one costs a full year or two —
that cost outweighs dependency weight in all realistic cases, hence the
100/50/0 spread vs. the smaller per-unlock increment.

### Composite priority for the solver's search order

```
priority_key = (locked ? 0 : 1, -tier_weight, -bottleneck_score)
```

Locked (manually overridden) courses always sort first — they are hard
constraints, not choices the search evaluates.

### Cross-program clash resolution

When two courses from *different* programs of the *same tier* clash on
time, resolve by bottleneck score alone (do not add extra tier weighting
between two majors — they're equal by design in v1).

---

## Credit-hour constraints

- Minimum 12 credit hours per semester, maximum 18.
- These are HARD bounds enforced by the solver during search (pruning), and
  again as a gate on manual overrides: an edit that would drop a semester
  below 12 or above 18 must be blocked before it reaches the solver, with a
  clear message to the student about why.

---

## Multiple sections per course

A course can have more than one `sections` row in the same term (e.g.
CS 210 offered both MWF 9am and TR 2pm). These are NOT independent
requirement slots — they're mutually exclusive alternatives for
satisfying that one course's requirement. The solver must:

1. Treat every section of the same course as alternative candidates,
   never add more than one section of the same `course_id` to a single
   semester's plan.
2. When multiple sections of a course are viable (no conflict with
   already-chosen courses), prefer whichever section actually produces
   the best overall schedule — i.e. the one that avoids conflicts with
   other high-priority courses, or that best supports fitting more
   required courses into the semester — not just the first one
   encountered in an arbitrary order.

This is real optimization surface the backtracking search needs to
cover, not just "pick any section of a required course." Verify
`catalog.py`'s candidate-building step actually generates one candidate
per section (not one per course, collapsing options prematurely), and
that the backtracking search in `scheduler_backtracking_sketch.py`
correctly excludes sibling sections of an already-chosen course from
the remaining candidate pool once one is picked.

## The solver (backtracking algorithm)

Solves one semester at a time. Reference implementation/sketch already
built and smoke-tested — see `scheduler_backtracking_sketch.py` in this
repo (or reconstruct from this spec if not present).

Core logic:
1. Separate candidates into `locked` (manual overrides — always included)
   and `choosable`.
2. Sort `choosable` by the composite priority key above.
3. Recursively try including each candidate in priority order; on a time
   conflict or exceeding `MAX_CREDITS`, backtrack and try excluding it.
4. Base case: valid schedule once `total_credits >= MIN_CREDITS` and no
   candidates remain to try.
5. In practice, if the priority ordering is doing its job, the solver
   rarely needs to backtrack — good ordering finds a solution close to
   immediately. Backtracking exists to correct the rare case where a
   lower-priority pick blocks a higher-priority one later in the order.

Known gaps in the reference sketch, to be completed during implementation:
- `has_time_conflict` is a placeholder equality check — needs real
  day/time interval overlap logic using `sections.start_time`/`end_time`.
- No prerequisite validation yet — add as another pruning condition
  (reject a candidate if its prerequisites aren't satisfied per
  `student_progress` + already-chosen courses in earlier semesters).
- Cycle detection for the prerequisite graph is NOT enforced at the DB
  level (Postgres can't easily express "no cycles" as a constraint) — must
  be handled in application code when the dependency graph is built.

---

## Re-solve cascade

Two distinct entry points trigger the same underlying re-solve mechanism:

**A. Manual override** (student swaps/adds/removes a course in a future
semester):
1. Lock the edited course as a hard constraint for that semester.
2. Walk the prerequisite dependency graph forward from the changed course
   to find the "blast radius" — which future semesters contain courses
   that depend on it, or whose credit-hour pacing shifted as a result.
3. Re-solve only the affected semesters, in order, each using the prior
   (possibly now-changed) semester's output as its starting state.
4. If the override drops a semester below 12 credits or pushes it above
   18, block the edit before it reaches the solver (see Credit-hour
   constraints above).
5. If the override causes a materially worse outcome (graduation delay,
   downstream conflict), flag the affected semester (`is_flagged = true`,
   set `flag_reason`) but still honor the student's choice and re-solve
   around it. The credit-hour bounds are the only hard block; everything
   else is a soft flag.

**B. Retroactive correction to onboarding data** (e.g., student forgot to
mark a course as `done`):
1. Update the relevant `student_progress` row(s).
2. Treat this as a broader blast radius — typically re-solve ALL
   uncommitted future semesters from the current point forward, since the
   foundational requirement pool just changed, not just one course's slot.
3. Past/completed semesters are never altered.

---

## Deferred algorithmic feature: lookahead tiebreaking (v2)

When two courses are near-tied on bottleneck score (a genuine toss-up, not
resolvable by the tier/score heuristic), the ideal behavior is to simulate
both resolutions forward using the re-solve cascade, compare the resulting
graduation projections, and keep whichever path graduates earlier (or has
fewer flagged semesters, if tied). This requires running the multi-semester
re-solve twice per ambiguous clash and is NOT part of v1 — the v1 solver
uses bottleneck score as a flat, immediate tiebreaker with no lookahead.
Do not implement this until the core single-pass solver and re-solve
cascade are working end-to-end and tested.

---

## Deferred feature: multi-scenario ("what-if") planning (v2)

Incoming freshmen (or any student) may want to explore multiple hypothetical
plans before committing — e.g. "what does my plan look like if I take AP
Calc vs. AP Stats." v1 supports exactly ONE committed plan per student. v2
would introduce a `plan_scenarios` table (student × scenario name ×
committed flag) that `semester_plans` belongs to instead of belonging
directly to a student, allowing N parallel draft plans with a comparison
view. Do not build this table or UI in v1 — it adds real complexity
(the solver must run independently per scenario) that isn't worth taking
on before the single-plan engine is proven.

---

## Database schema

Full schema in `schema.sql` in this repo. Postgres via Supabase.
`students.id` is a foreign key to `auth.users(id)` — Supabase Auth owns
identity; `students` extends it with profile/academic fields.

Tables: `students`, `programs`, `student_programs`, `courses`,
`prerequisites`, `degree_requirements`, `sections`, `student_progress`,
`semester_plans`.

Key relational design decisions:
- `programs.required_by_program_id` (self-referencing FK) encodes
  structurally-required minors.
- `prerequisites` (course → prerequisite_course, self-referencing through
  `courses`) is the dependency graph the solver and re-solve cascade walk.
- `degree_requirements` sits between `programs` and `courses` as its own
  table specifically so one course can satisfy requirements in multiple
  programs (double majors/minors) while `student_progress` still has only
  ONE row per student-course — "confirm once, applies everywhere."
- `semester_plans` is the solver's actual output: student × section × term,
  with `is_locked` and `is_flagged` booleans driving the UI and re-solve
  behavior described above.

Indexes exist on the four highest-frequency lookups: student progress by
student, semester plans by student+term, prerequisites by course, and
sections by course+term.

**Not yet defined:** Supabase Row Level Security policies. Must be written
before any real (even test) student accounts are used — students should
only be able to read/write their own rows in `students`,
`student_programs`, `student_progress`, and `semester_plans`. Catalog
tables (`programs`, `courses`, `prerequisites`, `degree_requirements`,
`sections`) are read-only for students, writable only by an admin/service
role.

---

## FastAPI endpoint structure

Auth itself (signup, login, password, email verification) is handled
client-side via the Supabase SDK — FastAPI never touches passwords. Every
protected FastAPI endpoint depends on a `get_current_student` dependency
that decodes the Supabase-issued JWT (via Supabase's published JWKS) to
get `auth.uid()` and load the matching `students` row.

- `POST /students/me` — create the `students` profile row immediately
  after Supabase signup (first/last name, school only —
  `class_standing`/`current_term` are nullable and NOT set here; see
  note below).
- `GET /students/me` — profile + onboarding status.
- `POST /students/me/programs` — declare majors/minors (bulk, onboarding
  step 1).
- `POST /students/me/progress` — bulk course status confirmation
  (onboarding step 3: done/in_progress/not_taken).
- `PATCH /students/me/progress/{course_id}` — single-course status
  correction. This is re-solve cascade entry point B (retroactive
  correction).

**Note on `students` nullability**: `class_standing` and `current_term`
are nullable in the schema, not required at row creation. A student row
must exist the moment email verification succeeds (so
`get_current_student` has something to load), but those two fields
genuinely aren't known until onboarding step 2 — an earlier draft of
this schema had them as `NOT NULL`, which was a real conflict with this
endpoint's own description; see `migration_001_nullable_onboarding_fields.sql`
for the fix if working against an already-applied database.
`students.onboarding_completed_at` (timestamptz, null until set) is the
explicit signal for "has this student finished onboarding" — set it once
onboarding step 3 (course history confirmation) completes. Don't infer
onboarding status from `class_standing IS NULL` — the explicit timestamp
is unambiguous where that would be fragile.
- `GET /courses`, `GET /programs`, `GET /courses/{id}/sections?term=` —
  catalog reads.
- `POST /schedule/optimize` — run the solver fresh for a student. Used
  right after onboarding, and internally by the retroactive-correction
  cascade.
- `POST /schedule/override` — manual edit to a specific semester's plan
  (swap/add/remove a course). This is re-solve cascade entry point A
  (blast-radius walk + targeted re-solve).
- `GET /schedule/me?term=` — current committed plan for a given term.
- `GET /schedule/me/projection` — graduation date estimate + credit
  hour summary (taken/in-progress/remaining).

## Auth: restrict signups to ORU email

Supabase Auth has no built-in "restrict to this domain" setting. Enforce
`@oru.edu` in two places:

1. **Client-side** (signup form): immediate, friendly validation —
   "Please use your ORU email" — this is UX only, not the security
   boundary, since it can be bypassed.
2. **Server-side** (the actual gate): a Supabase **"Before User Created"
   Auth Hook** (implemented as a Postgres function or HTTP endpoint) that
   inspects the incoming email and rejects the signup if the domain
   isn't `@oru.edu`. This is Supabase's current supported mechanism for
   this — prefer it over the older community pattern of a raw trigger on
   `auth.users`, which has a known issue where exceptions don't always
   bubble a clean error message back to the client (the user would just
   see a generic failure instead of the actual reason).

## Supabase Row Level Security

Enable RLS on every table. Two policy patterns:

- **Student-owned tables** (`students`, `student_programs`,
  `student_progress`, `semester_plans`): restrict `select`/`insert`/
  `update`/`delete` to `auth.uid() = student_id` (or `= id` on
  `students` itself). A student can only ever read/write their own rows.
- **Catalog tables** (`programs`, `courses`, `prerequisites`,
  `degree_requirements`, `sections`): `select` open to the
  `authenticated` role; `insert`/`update`/`delete` restricted to
  `service_role` only (admin/seed scripts write the catalog, students
  only ever read it).

See `rls_policies.sql` in this repo for the actual policy statements.

## Frontend structure

List view and calendar-grid view are not competing choices — they answer
different questions and are both used:

- **List/card view** — one card per semester, across the full
  multi-semester outlook. Shows recommended courses, credit total, and
  flag status per semester. A calendar grid doesn't make sense across 8
  semesters simultaneously, so this is the primary outlook view.
- **Calendar grid view** — days × times, for whichever ONE semester is
  currently selected/expanded. This is where actual time-conflict
  overrides happen (clicking a slot opens the override modal).

Component sketch:
```
Dashboard
├── CreditProgressBar        (taken / in-progress / remaining)
├── GraduationProjectionCard (month/year, updates live on edits)
├── SemesterOutlookList      (cards, one per semester, click to expand)
│   └── SemesterCalendarGrid (expanded semester's weekly time layout)
│       └── CourseOverrideModal (triggered from a grid slot)
└── FlagBadge                (rendered on flagged cards/slots, shows flag_reason)
```

## Redis caching

Cache key shape: `schedule:{student_id}:{term}` — serialized solver
output for that semester.

Invalidation: on any of the three mutation points below, delete all keys
matching `schedule:{student_id}:*` for that student (simpler and safe
given object sizes — no need for surgical per-term invalidation even
though the blast-radius walk already knows which terms changed):
1. `student_progress` change (retroactive correction)
2. `semester_plans` override (manual edit)
3. Any full re-solve cascade run

1-hour TTL as a backstop against any missed invalidation path.

## Real day/time overlap logic (updated — section_meetings)

**This changed from the original single-meeting model.** Real Fall 2026
registration data surfaced that a single section can have more than one
distinct meeting pattern in the same term — e.g. CSC 255 Data
Structures, section 01: MWF 8:40-9:35 AM AND separately Tuesday
10:40-11:55 AM, both under one section (a lecture block plus a separate
discussion block). The original `sections.days`/`start_time`/`end_time`
columns could only hold one pattern — real risk of silently dropping a
real meeting and missing a real conflict, which would undercut the
actual thing this project demonstrates.

**Fixed via `migration_003_section_meetings.sql`**: meeting times moved
to a new one-to-many `section_meetings` table (`section_id`, `days`,
`start_time`, `end_time`). A section with one meeting pattern (the
common case) has one row; a section with a lecture-plus-lab split has
two or more. See `schema.sql` for the current structure.

**Conflict check must now compare across ALL meeting rows for both
sections**, not a single day/time pair:

```python
def has_time_conflict(section_a: Section, section_b: Section) -> bool:
    for meeting_a in section_a.meetings:
        for meeting_b in section_b.meetings:
            shares_day = any(d in meeting_b.days for d in meeting_a.days)
            overlaps_time = (
                meeting_a.start_time < meeting_b.end_time
                and meeting_b.start_time < meeting_a.end_time
            )
            if shares_day and overlaps_time:
                return True
    return False
```

This means `scheduler_backtracking_sketch.py`'s `Section` dataclass
needs to change from a single `day_time: tuple[str, ...]` field to a
`meetings: list[Meeting]` field (or equivalent), and `catalog.py`'s
row-loading needs to join `section_meetings` and group by
`section_id` when building solver input.

## Cost/tuition delta

Deliberately simple for v1 — this is a small utility function, not a
subsystem:

```
cost(credit_hours) = credit_hours * RATE_PER_CREDIT_HOUR
extension_cost(extra_semesters) = extra_semesters * (AVG_SEMESTER_CREDITS * RATE_PER_CREDIT_HOUR + FLAT_FEE)
```

`RATE_PER_CREDIT_HOUR` and `FLAT_FEE` are config constants, not a database
table — do not model tuition tiers/scholarships/aid in v1.

## CI/CD (GitHub Actions)

On push/PR to `main`:
1. Lint (ruff or flake8)
2. Run pytest
3. Build the Docker image (verify it builds — don't need to push yet on
   PR runs)

On merge to `main` only:
4. Trigger Render deploy via Render's deploy-hook URL (a webhook POST,
   configured as a GitHub Actions secret — no Render API token handling
   needed beyond the hook URL itself).

See `ci-workflow.yml` in this repo for the actual workflow file
(intended path once added to a repo: `.github/workflows/ci.yml`).

---

## Still open (genuinely deferred, not yet worth designing)

- Sofia Learning / community college transfer credit equivalency data
- Department-facing analytics UI (synthetic data only, v1 stretch at best)
- Multi-scenario planning implementation (v2, see above)
- Lookahead tiebreaking implementation (v2, see above)
