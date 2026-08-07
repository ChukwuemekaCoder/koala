"""
Turns Postgres rows into the Course/Section/Candidate objects
scheduler_backtracking_sketch.py operates on: declared programs -> tier
assignment, remaining degree requirements, prerequisite graph +
unlocks_count + cycle detection, and per-term section/candidate building.
"""

from dataclasses import dataclass

import asyncpg

from app.solver.scheduler_backtracking_sketch import (
    TIER_GENED,
    TIER_MAJOR,
    TIER_MINOR,
    Candidate,
    Course,
    Section,
)

_MAJOR_CATEGORIES = {"major_core", "major_elective"}
_GENED_CATEGORIES = {"gen_ed", "christian_coursework"}


class PrerequisiteCycleError(Exception):
    """The prerequisite graph among a student's remaining courses has a
    cycle — a catalog data bug, not something that should happen with
    legitimate course data. Not enforceable at the DB level (see
    CLAUDE.md), so it's checked here whenever the graph is built."""


@dataclass
class RequiredCourse:
    course: Course
    tier: int


async def load_declared_program_ids(
    pool: asyncpg.Pool, student_id: str
) -> list[str]:
    rows = await pool.fetch(
        "select program_id from student_programs where student_id = $1",
        student_id,
    )
    return [str(r["program_id"]) for r in rows]


async def load_completed_course_ids(
    pool: asyncpg.Pool, student_id: str
) -> set[str]:
    """
    Courses already 'done' or 'in_progress' per student_progress — the
    other half of prerequisite satisfaction alongside courses the solver
    has already chosen in earlier semesters of the current run (see
    cascade.resolve_from_term). These courses are excluded from
    `remaining` (load_remaining_requirements already filters them out),
    so without this, a completed prerequisite would look unsatisfied.
    """
    rows = await pool.fetch(
        """
        select course_id from student_progress
        where student_id = $1 and status in ('done', 'in_progress')
        """,
        student_id,
    )
    return {str(r["course_id"]) for r in rows}


async def load_remaining_requirements(
    pool: asyncpg.Pool, student_id: str
) -> dict[str, RequiredCourse]:
    """
    Everything the student still needs: courses required by their
    declared programs, minus anything already 'done' or 'in_progress',
    with tier assigned per the priority system, prerequisites loaded,
    unlocks_count computed against this same remaining pool, and the
    prerequisite subgraph checked for cycles.
    """
    declared_ids = await load_declared_program_ids(pool, student_id)
    if not declared_ids:
        return {}
    return await _remaining_requirements_for_declared_programs(
        pool, student_id, declared_ids
    )


async def _remaining_requirements_for_declared_programs(
    pool: asyncpg.Pool, student_id: str, declared_ids: list[str]
) -> dict[str, RequiredCourse]:
    """
    Split out from load_remaining_requirements() so it's testable against
    real seeded catalog data by passing declared_ids directly, without
    needing a real students/student_programs row — every query here is a
    read-only SELECT, so a syntactically-valid but non-existent
    student_id is harmless (no FK is enforced on reads).
    """
    program_rows = await pool.fetch(
        "select id, required_by_program_id from programs"
    )
    # program_id -> the program that requires it (None if none does).
    # A minor is promoted to TIER_MAJOR when the program requiring it is
    # itself declared — NOT when the minor itself appears as a value
    # elsewhere (that's a different, unrelated program's relationship).
    requiring_program_of = {
        str(r["id"]): str(r["required_by_program_id"])
        for r in program_rows
        if r["required_by_program_id"] is not None
    }

    declared_set = set(declared_ids)

    req_rows = await pool.fetch(
        """
        select dr.course_id, dr.program_id, dr.category,
               c.code, c.title, c.credit_hours, c.offering_frequency
        from degree_requirements dr
        join courses c on c.id = dr.course_id
        where dr.program_id = any($1::uuid[])
          and c.id not in (
            select course_id from student_progress
            where student_id = $2 and status in ('done', 'in_progress')
          )
        """,
        list(declared_set),
        student_id,
    )

    remaining: dict[str, RequiredCourse] = {}
    for row in req_rows:
        course_id = str(row["course_id"])
        category = row["category"]
        program_id = str(row["program_id"])

        if category in _MAJOR_CATEGORIES:
            tier = TIER_MAJOR
        elif category in _GENED_CATEGORIES:
            tier = TIER_GENED
        else:  # 'minor'
            requiring_program = requiring_program_of.get(program_id)
            tier = TIER_MAJOR if requiring_program in declared_set else TIER_MINOR

        if course_id in remaining:
            remaining[course_id].tier = max(remaining[course_id].tier, tier)
        else:
            remaining[course_id] = RequiredCourse(
                course=Course(
                    id=course_id,
                    credit_hours=row["credit_hours"],
                    offering_frequency=row["offering_frequency"],
                    code=row["code"],
                    title=row["title"],
                ),
                tier=tier,
            )

    await _load_prerequisites_and_unlocks(pool, remaining)
    return remaining


async def _load_prerequisites_and_unlocks(
    pool: asyncpg.Pool, remaining: dict[str, RequiredCourse]
) -> None:
    if not remaining:
        return

    course_ids = list(remaining.keys())
    prereq_rows = await pool.fetch(
        """
        select course_id, prerequisite_course_id
        from prerequisites
        where course_id = any($1::uuid[])
        """,
        course_ids,
    )

    edges: dict[str, list[str]] = {cid: [] for cid in course_ids}
    for row in prereq_rows:
        course_id = str(row["course_id"])
        prereq_id = str(row["prerequisite_course_id"])
        edges[course_id].append(prereq_id)
        remaining[course_id].course.prereq_ids.append(prereq_id)

    _check_for_cycles(edges)
    recompute_unlocks_count(remaining)


def recompute_unlocks_count(remaining: dict[str, RequiredCourse]) -> None:
    """
    Recomputes each remaining course's unlocks_count against the
    *current* remaining pool (mutates in place). Call this again as the
    pool shrinks across a multi-semester cascade — a course's
    unlocks_count should reflect how many OTHER still-remaining courses
    need it, not a count frozen at the start of the whole plan.
    """
    for required in remaining.values():
        required.course.unlocks_count = sum(
            1
            for other in remaining.values()
            if required.course.id in other.course.prereq_ids
        )


def _check_for_cycles(edges: dict[str, list[str]]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in edges}

    def visit(node: str) -> None:
        color[node] = GRAY
        for neighbor in edges.get(node, []):
            if neighbor not in color:
                continue  # prereq outside the remaining subgraph — not our concern here
            if color[neighbor] == GRAY:
                raise PrerequisiteCycleError(
                    f"Circular prerequisite dependency detected involving course {neighbor}"
                )
            if color[neighbor] == WHITE:
                visit(neighbor)
        color[node] = BLACK

    for node in list(edges):
        if color[node] == WHITE:
            visit(node)


async def load_term_candidates(
    pool: asyncpg.Pool,
    remaining: dict[str, RequiredCourse],
    term: str,
    exclude_course_ids: frozenset[str] = frozenset(),
) -> list[Candidate]:
    """
    One Candidate per remaining, non-excluded required course that has a
    section offered this term. If a course has multiple sections in the
    term, picks one deterministically (lowest section id) — the core
    solver assumes exactly one section per course per candidate set.
    """
    course_ids = [
        cid for cid in remaining if cid not in exclude_course_ids
    ]
    if not course_ids:
        return []

    rows = await pool.fetch(
        """
        select distinct on (course_id)
            id, course_id, days, start_time, end_time
        from sections
        where term = $1 and course_id = any($2::uuid[])
        order by course_id, id
        """,
        term,
        course_ids,
    )

    candidates = []
    for row in rows:
        course_id = str(row["course_id"])
        required = remaining[course_id]
        section = Section(
            id=str(row["id"]),
            course_id=course_id,
            days=row["days"],
            start_time=row["start_time"],
            end_time=row["end_time"],
        )
        candidates.append(Candidate(course=required.course, section=section, tier=required.tier))
    return candidates


async def load_locked_candidates(
    pool: asyncpg.Pool,
    remaining: dict[str, RequiredCourse],
    student_id: str,
    term: str,
) -> list[Candidate]:
    """
    Existing manually-overridden (is_locked) semester_plans rows for this
    student+term, rebuilt as hard-constraint Candidates.
    """
    rows = await pool.fetch(
        """
        select se.id as section_id, se.course_id, se.days, se.start_time, se.end_time,
               c.code, c.title, c.credit_hours, c.offering_frequency
        from semester_plans sp
        join sections se on se.id = sp.section_id
        join courses c on c.id = se.course_id
        where sp.student_id = $1 and sp.term = $2 and sp.is_locked = true
        """,
        student_id,
        term,
    )

    candidates = []
    for row in rows:
        course_id = str(row["course_id"])
        required = remaining.get(course_id)
        if required is not None:
            course = required.course
            tier = required.tier
        else:
            # Locked but no longer tied to a remaining requirement (e.g.
            # satisfied elsewhere already) — tier is irrelevant since
            # locked candidates always sort first regardless of tier.
            course = Course(
                id=course_id,
                code=row["code"],
                title=row["title"],
                credit_hours=row["credit_hours"],
                offering_frequency=row["offering_frequency"],
            )
            tier = TIER_GENED
        section = Section(
            id=str(row["section_id"]),
            course_id=course_id,
            days=row["days"],
            start_time=row["start_time"],
            end_time=row["end_time"],
        )
        candidates.append(Candidate(course=course, section=section, tier=tier, locked=True))
    return candidates
