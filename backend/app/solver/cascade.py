"""
Multi-semester walk-forward solve: repeatedly calls solve_semester() for
successive terms until the student's remaining degree requirements are
exhausted, or a safety cap is hit. This is the shared mechanism behind
both re-solve cascade entry points in CLAUDE.md — POST /schedule/optimize
starts it from the student's current term; POST /schedule/override
starts it from the edited term (the override's blast radius, since a
credit-hour pacing shift can affect everything downstream).
"""

from dataclasses import dataclass
from datetime import date

import asyncpg

from app.solver.catalog import (
    load_completed_course_ids,
    load_locked_candidates,
    load_remaining_requirements,
    load_term_candidates,
    recompute_unlocks_count,
)
from app.solver.scheduler_backtracking_sketch import (
    MAX_CREDITS,
    Candidate,
    solve_semester,
)

MAX_SEMESTERS = 16


@dataclass
class SemesterResult:
    term: str
    chosen: list[Candidate]
    feasible: bool


@dataclass
class CascadeResult:
    semesters: list[SemesterResult]
    graduated: bool  # remaining requirements fully exhausted


def current_term_label(declared_term: str | None = None, today: date | None = None) -> str:
    """
    'Fall <year>' or 'Spring <year>' — matches the free-text convention
    sections.term/semester_plans.term already use. students.current_term
    only stores 'fall'/'spring' with no year, so the real current year is
    always derived from the real calendar date.

    If the student has declared a current_term (set during onboarding —
    lets a student starting off-cycle or ahead/behind say which term
    they're actually in), that season is honored over the wall-clock
    season. Before onboarding sets it (current_term is nullable and
    starts null), this falls back to whatever season it actually is.
    """
    today = today or date.today()  # noqa: DTZ011 — local calendar term, not tz-sensitive date math
    wall_clock_season = "Fall" if 8 <= today.month <= 12 else "Spring"
    season = declared_term.capitalize() if declared_term else wall_clock_season
    return f"{season} {today.year}"


def next_term_label(term: str) -> str:
    season, year_str = term.split()
    year = int(year_str)
    if season == "Fall":
        return f"Spring {year + 1}"
    return f"Fall {year}"


def terms_before(target_term: str, start_term: str | None = None) -> list[str]:
    """
    Canonical term labels from `start_term` (default: the real current
    term) up to but excluding `target_term`, walking the fall/spring
    sequence. Used to find which semesters come "before" an edited term
    without relying on string comparison (term labels don't sort
    chronologically as plain text — "Fall 2026" < "Spring 2026"
    alphabetically despite being later in the calendar).
    """
    start_term = start_term or current_term_label()
    terms = []
    term = start_term
    for _ in range(MAX_SEMESTERS):
        if term == target_term:
            break
        terms.append(term)
        term = next_term_label(term)
    return terms


async def load_existing_future_terms(
    pool: asyncpg.Pool, student_id: str, from_term: str
) -> list[str]:
    """
    Which terms >= from_term (chronologically) currently have
    semester_plans rows for this student — walks the canonical sequence
    and checks existence, same reasoning as terms_before().
    """
    rows = await pool.fetch(
        "select distinct term from semester_plans where student_id = $1", student_id
    )
    existing = {r["term"] for r in rows}
    result = []
    term = from_term
    for _ in range(MAX_SEMESTERS):
        if term in existing:
            result.append(term)
        term = next_term_label(term)
    return result


async def resolve_from_term(
    pool: asyncpg.Pool,
    student_id: str,
    start_term: str,
    completed_course_ids: set[str] | None = None,
) -> CascadeResult:
    """
    Walks forward from `start_term`, solving one semester at a time,
    until the student's remaining degree requirements are exhausted or
    MAX_SEMESTERS is hit. Prerequisite satisfaction draws on both halves
    CLAUDE.md specifies: what's 'done'/'in_progress' in student_progress
    (always included), plus whatever extra `completed_course_ids` the
    caller passes in — the override cascade uses this to credit courses
    already scheduled in semesters before `start_term`.
    """
    remaining = await load_remaining_requirements(pool, student_id)
    satisfied = await load_completed_course_ids(pool, student_id)
    satisfied |= set(completed_course_ids or set())
    # Anything already satisfied — including courses locked into earlier,
    # preserved semesters by the caller — must never be re-scheduled.
    for course_id in satisfied:
        remaining.pop(course_id, None)

    semesters: list[SemesterResult] = []
    term = start_term

    for _ in range(MAX_SEMESTERS):
        if not remaining:
            return CascadeResult(semesters=semesters, graduated=True)

        recompute_unlocks_count(remaining)

        locked = await load_locked_candidates(pool, remaining, student_id, term)
        locked_course_ids = frozenset(c.course.id for c in locked)
        choosable = await load_term_candidates(
            pool, remaining, term, exclude_course_ids=locked_course_ids
        )

        # If everything still remaining could fit in one semester, this
        # is (at most) the final semester — don't require a full 12
        # credits just because there's nothing left to pad it with.
        remaining_total_credits = sum(
            rc.course.credit_hours for rc in remaining.values()
        )
        min_credits = 0 if remaining_total_credits <= MAX_CREDITS else None

        chosen = solve_semester(
            locked + choosable,
            completed_course_ids=satisfied,
            **({"min_credits": min_credits} if min_credits is not None else {}),
        )

        if chosen is None:
            semesters.append(SemesterResult(term=term, chosen=[], feasible=False))
            return CascadeResult(semesters=semesters, graduated=False)

        semesters.append(SemesterResult(term=term, chosen=chosen, feasible=True))

        for candidate in chosen:
            satisfied.add(candidate.course.id)
            remaining.pop(candidate.course.id, None)

        term = next_term_label(term)

    return CascadeResult(semesters=semesters, graduated=not remaining)
