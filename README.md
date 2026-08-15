# koala

**Know when you'll graduate — and exactly what it takes.**

koala is a degree-planning platform for Oral Roberts University students
that automatically builds and re-optimizes a multi-semester course
schedule around each student's majors, minors, and graduation timeline 
using a constraint-satisfaction backtracking solver, not a trained model.

🔗 **Live app:** [koala-woad.vercel.app](https://koala-woad.vercel.app)

---

## The problem

Every year, ORU students fall behind their expected graduation date —
not because they don't plan, but because the planning problem is
genuinely hard to do by hand. Gen-ed and Christian coursework
requirements compete with major coursework for a limited number of
semesters. Faculty and timetable shortages mean required courses clash
or are only offered once a year. And no advisor can realistically
compute the mathematically optimal path through hundreds of course/time
combinations for every student they meet with.

koala treats this as what it actually is: a constraint optimization
problem, and solves it as one.

## How it works

**This is not AI.** koala's recommendation engine is a backtracking
constraint-satisfaction solver — deterministic, explainable, and testable
— not a trained or generative model. Every schedule it produces can be
traced back to the exact rule that produced it.

- **Priority-tiered course selection** — structurally-required minors
  (e.g. a Computer Science major requiring a Math minor) are
  automatically promoted to the same priority as the major itself;
  declared majors outrank elective minors, which outrank gen-eds.
- **Bottleneck scoring** — courses offered less often (annually or
  biennially) are prioritized over courses offered every semester,
  weighted further by how many other remaining courses depend on them.
- **Multi-section optimization** — when a course has more than one
  offered section (different days/times), the solver picks whichever
  section produces the best overall schedule, not just the first one
  found.
- **Real multi-meeting conflict detection** — a single section can meet
  at genuinely different day/time patterns in the same term (a lecture
  block plus a separate discussion block); the solver checks every
  meeting pair, not just one.
- **Prerequisite-aware, cycle-safe** — courses with unmet prerequisites
  are excluded from consideration; the prerequisite graph is checked for
  cycles via depth-first search before it's ever used.
- **Hard credit-hour bounds** (12–18/semester) enforced before the
  solver runs, not discovered after the fact.
- **A re-solve cascade with two entry points** — a manual override
  (swap, add, or remove a course) walks the dependency graph forward and
  re-solves only the affected future semesters; a retroactive correction
  (e.g. "I forgot to mark this course as done") re-solves everything
  from the current point forward, since the whole requirement pool just
  shifted.

## Features

- **Live graduation projection** that updates in real time as you edit
  your plan — see exactly what a change costs before you commit to it.
- **Full onboarding flow** — program selection with auto-detected
  required minors, class standing/term, and course history confirmation,
  built around search-and-filter rather than scrolling a static list.
- **Dashboard** — a semester-by-semester progress timeline, credit-hour
  breakdown, a scannable multi-semester outlook, and a real weekly
  calendar grid per semester.
- **Override and add-course modals** that surface the credit-bound rules
  directly — a blocked action tells you exactly why and what to do
  instead, never a silent rejection.
- **@oru.edu-restricted signup**, enforced server-side via a Supabase
  Auth hook, not just a client-side check.

## Architecture & tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python), containerized with Docker |
| Database | PostgreSQL via Supabase, with row-level security on every table |
| Auth | Supabase Auth (email verification, server-enforced domain restriction) |
| Caching | Redis |
| Frontend | React + TypeScript, Vite |
| Backend hosting | Render |
| Frontend hosting | Vercel |
| CI/CD | GitHub Actions — lint, full test suite, Docker build, and automated deploy on every push to main |

The schema models real structural complexity, not a flattened version of
it: a self-referencing `programs` table encodes structurally-required
minors, a self-referencing `prerequisites` table forms the dependency
graph the solver walks, and `sections`/`section_meetings` are split into
a proper one-to-many relationship so a single section with a
lecture-plus-lab split is represented correctly instead of silently
collapsed into one meeting time.

### A few real bugs this project caught during development, not just claimed to prevent

- A tier-promotion check had the "required by" relationship backwards —
  would have silently mis-prioritized every structurally-required minor.
- The re-solve cascade wasn't pulling a student's already-completed
  courses into prerequisite checks, meaning a student who'd already
  earned a prerequisite could have dependent courses wrongly excluded.
- A `DISTINCT ON` in the catalog-loading query was collapsing multiple
  real sections of the same course down to one *before* the solver ever
  saw the alternatives — quietly defeating the entire multi-section
  optimization feature.
- The override endpoint's "add a course" path had no check for a course
  already committed to a different semester, which could have let the
  same requirement get satisfied twice.

## Getting started

```bash
git clone https://github.com/ChukwuemekaCoder/koala.git
cd koala

# Backend + Redis
docker compose up --build

# Frontend, in a separate terminal
cd frontend
npm install
npm run dev
```

You'll need a `.env` file with `DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `REDIS_URL` for the
backend, and `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`,
`VITE_API_URL` for the frontend. Run `schema.sql` and `rls_policies.sql`
(plus any numbered migrations) against your own Supabase project before
starting the backend.

## Testing

```bash
cd backend
pytest -v
```

77 tests covering solver edge cases (time-conflict overlap, prerequisite
pruning, cycle detection, multi-section selection), catalog-loading
logic against seeded data, endpoint contracts, and a genuine end-to-end
integration test that creates a real Supabase user via the Auth Admin
API and drives actual HTTP requests through the full onboarding →
optimize → override flow.

## Data & scope

koala is intentionally scoped to **undergraduate ORU students only** —
graduate programs don't share undergraduate's gen-ed/Christian
coursework structure and would need a genuinely different requirement
model.

Course and program data is drawn from ORU's real public catalog and
degree plan sheets, hand-compiled rather than scraped. Section meeting
times are realistic but synthetic — koala has no connection to (and
never automates against) ORU's actual login-walled registration system.
Some prerequisite relationships are sequence-informed inferences from
real degree plans rather than verified against the current course
catalog. None of this touches real student records; there is no live
connection to ORU's official systems.

**Worth noting:** ORU already uses Degree Works for official degree
tracking through the registrar. koala isn't trying to replace it — it
demonstrates the constraint-based multi-semester optimization and
live "what does this change cost me" feedback that a standard degree
audit tool doesn't attempt.

### Deliberately deferred (v2)

- Lookahead tiebreaking — when two courses are genuinely tied on
  priority, simulating both resulting schedules forward and keeping
  whichever graduates earlier, rather than a single-pass heuristic.
- Multi-scenario "what if" planning — comparing multiple hypothetical
  plans side by side (useful for an incoming freshman deciding between
  AP credit paths, for example).
- Transfer credit and external providers (e.g. Sofia Learning).
- Department-facing analytics on section timing preferences.
