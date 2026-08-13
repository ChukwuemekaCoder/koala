from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import cache
from app.auth import get_current_student
from app.db import get_pool
from app.solver import cascade, catalog
from app.solver.scheduler_backtracking_sketch import MAX_CREDITS, MIN_CREDITS, Candidate

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _serialize_candidate(
    candidate: Candidate,
    category: str = "major",
    is_flagged: bool = False,
    flag_reason: str | None = None,
) -> dict:
    return {
        "course_id": candidate.course.id,
        "code": candidate.course.code,
        "title": candidate.course.title,
        "credit_hours": candidate.course.credit_hours,
        "category": category,
        "section_id": candidate.section.id,
        "meetings": [
            {
                "days": m.days,
                "start_time": m.start_time.isoformat(),
                "end_time": m.end_time.isoformat(),
            }
            for m in candidate.section.meetings
        ],
        "is_locked": candidate.locked,
        "is_flagged": is_flagged,
        "flag_reason": flag_reason,
    }


def _serialize_cascade(
    result: cascade.CascadeResult,
    categories: dict[str, str] | None = None,
    flagged_terms: dict[str, str] | None = None,
) -> dict:
    categories = categories or {}
    flagged_terms = flagged_terms or {}
    semesters = []
    for semester in result.semesters:
        flag_reason = flagged_terms.get(semester.term)
        semesters.append(
            {
                "term": semester.term,
                "feasible": semester.feasible,
                "total_credits": sum(c.course.credit_hours for c in semester.chosen),
                "is_flagged": flag_reason is not None,
                "flag_reason": flag_reason,
                "courses": [
                    _serialize_candidate(
                        c,
                        category=categories.get(c.course.id, "major"),
                        is_flagged=flag_reason is not None,
                        flag_reason=flag_reason,
                    )
                    for c in semester.chosen
                ],
            }
        )
    return {"graduated": result.graduated, "semesters": semesters}


async def _persist_cascade_result(
    student_id: str,
    result: cascade.CascadeResult,
    flagged_terms: dict[str, str] | None = None,
) -> None:
    flagged_terms = flagged_terms or {}
    pool = get_pool()
    for semester in result.semesters:
        # Clear stale choosable picks for this term; locked rows are
        # re-inserted (upserted) below, never dropped.
        await pool.execute(
            "delete from semester_plans where student_id = $1 and term = $2 and is_locked = false",
            student_id,
            semester.term,
        )
        flag_reason = flagged_terms.get(semester.term)
        for candidate in semester.chosen:
            await pool.execute(
                """
                insert into semester_plans
                    (student_id, section_id, term, is_locked, is_flagged, flag_reason)
                values ($1, $2, $3, $4, $5, $6)
                on conflict (student_id, section_id) do update
                    set term = excluded.term,
                        is_locked = excluded.is_locked,
                        is_flagged = excluded.is_flagged,
                        flag_reason = excluded.flag_reason
                """,
                student_id,
                candidate.section.id,
                semester.term,
                candidate.locked,
                flag_reason is not None,
                flag_reason,
            )


async def _cleanup_orphaned_terms(
    student_id: str, touched_terms: set[str]
) -> None:
    """
    A fresh full re-solve (optimize, or a cascade-B retroactive
    correction) can produce a shorter plan than what existed before
    (e.g. after requirements changed) — clean up now-orphaned choosable
    rows in terms the new plan didn't touch. Locked rows are left alone;
    they're hard constraints the student set explicitly.
    """
    pool = get_pool()
    existing_terms = await pool.fetch(
        "select distinct term from semester_plans where student_id = $1", student_id
    )
    for row in existing_terms:
        if row["term"] not in touched_terms:
            await pool.execute(
                "delete from semester_plans where student_id = $1 and term = $2 and is_locked = false",
                student_id,
                row["term"],
            )


@router.post("/optimize")
async def optimize(student: dict = Depends(get_current_student)) -> dict:
    student_id = str(student["id"])
    pool = get_pool()

    declared = await catalog.load_declared_program_ids(pool, student_id)
    if not declared:
        raise HTTPException(
            422, "Declare at least one major or minor before generating a schedule"
        )

    start_term = cascade.current_term_label(student.get("current_term"))
    result = await cascade.resolve_from_term(pool, student_id, start_term)
    await _persist_cascade_result(student_id, result)
    await _cleanup_orphaned_terms(student_id, {s.term for s in result.semesters})
    await cache.invalidate_schedule_cache(student_id)

    categories = await catalog.load_course_categories(pool, student_id)
    return _serialize_cascade(result, categories=categories)


class OverrideRequest(BaseModel):
    term: str
    remove_course_id: str | None = None
    add_section_id: str | None = None


@router.post("/override")
async def override(
    body: OverrideRequest, student: dict = Depends(get_current_student)
) -> dict:
    student_id = str(student["id"])
    pool = get_pool()

    if not body.remove_course_id and not body.add_section_id:
        raise HTTPException(
            422, "Specify a course to remove, a section to add, or both"
        )

    current_rows = await pool.fetch(
        """
        select sp.section_id, se.course_id, c.credit_hours
        from semester_plans sp
        join sections se on se.id = sp.section_id
        join courses c on c.id = se.course_id
        where sp.student_id = $1 and sp.term = $2
        """,
        student_id,
        body.term,
    )
    current_total = sum(r["credit_hours"] for r in current_rows)

    remove_section_id = None
    removed_credits = 0
    if body.remove_course_id:
        match = next(
            (r for r in current_rows if str(r["course_id"]) == body.remove_course_id),
            None,
        )
        if match is None:
            raise HTTPException(404, "That course isn't in this semester's plan")
        remove_section_id = match["section_id"]
        removed_credits = match["credit_hours"]

    added_credits = 0
    if body.add_section_id:
        add_row = await pool.fetchrow(
            """
            select se.course_id, c.credit_hours
            from sections se join courses c on c.id = se.course_id
            where se.id = $1
            """,
            body.add_section_id,
        )
        if add_row is None:
            raise HTTPException(404, "That section doesn't exist")

        remaining = await catalog.load_remaining_requirements(pool, student_id)
        if str(add_row["course_id"]) not in remaining:
            raise HTTPException(
                422, "That course doesn't count toward any of your remaining requirements"
            )
        added_credits = add_row["credit_hours"]

    prospective_total = current_total - removed_credits + added_credits

    if body.remove_course_id and not body.add_section_id and prospective_total < MIN_CREDITS:
        raise HTTPException(
            422,
            f"Removing this drops you to {prospective_total} credit hours, "
            f"below the {MIN_CREDITS}-hour minimum — add a replacement first",
        )
    if added_credits and prospective_total > MAX_CREDITS:
        raise HTTPException(
            422,
            f"Adding this would put you at {prospective_total} credit hours, "
            f"above the {MAX_CREDITS}-hour maximum",
        )

    # Snapshot downstream state before applying the edit, to diff against
    # after the re-solve and decide what to soft-flag.
    future_terms = await cascade.load_existing_future_terms(pool, student_id, body.term)
    before_snapshot: dict[str, set[str]] = {}
    for term in future_terms:
        rows = await pool.fetch(
            """
            select se.course_id from semester_plans sp
            join sections se on se.id = sp.section_id
            where sp.student_id = $1 and sp.term = $2
            """,
            student_id,
            term,
        )
        before_snapshot[term] = {str(r["course_id"]) for r in rows}

    async with pool.acquire() as conn, conn.transaction():
        if remove_section_id:
            await conn.execute(
                "delete from semester_plans where student_id = $1 and section_id = $2",
                student_id,
                remove_section_id,
            )
        if body.add_section_id:
            await conn.execute(
                """
                insert into semester_plans (student_id, section_id, term, is_locked)
                values ($1, $2, $3, true)
                on conflict (student_id, section_id) do update
                    set term = excluded.term, is_locked = true
                """,
                student_id,
                body.add_section_id,
                body.term,
            )

    prior_terms = cascade.terms_before(body.term)
    prior_course_ids: set[str] = set()
    if prior_terms:
        rows = await pool.fetch(
            """
            select se.course_id from semester_plans sp
            join sections se on se.id = sp.section_id
            where sp.student_id = $1 and sp.term = any($2::text[])
            """,
            student_id,
            prior_terms,
        )
        prior_course_ids = {str(r["course_id"]) for r in rows}

    result = await cascade.resolve_from_term(
        pool, student_id, body.term, completed_course_ids=prior_course_ids
    )

    flagged_terms: dict[str, str] = {}
    for semester in result.semesters:
        if semester.term == body.term:
            continue  # the directly-edited term is an intentional change, not a ripple effect
        before_ids = before_snapshot.get(semester.term)
        if before_ids is None:
            continue  # a newly-added semester, not a change to an existing one
        after_ids = {c.course.id for c in semester.chosen}
        if not semester.feasible:
            flagged_terms[semester.term] = (
                "This semester could no longer be fully planned because of an earlier edit"
            )
        elif after_ids != before_ids:
            flagged_terms[semester.term] = "This semester changed because of an earlier edit"

    await _persist_cascade_result(student_id, result, flagged_terms=flagged_terms)
    await cache.invalidate_schedule_cache(student_id)

    categories = await catalog.load_course_categories(pool, student_id)
    return _serialize_cascade(result, categories=categories, flagged_terms=flagged_terms)


def _group_meetings_by_section(rows: list[dict], categories: dict[str, str]) -> list[dict]:
    """
    Groups flat (one-row-per-meeting) SQL rows into one course dict per
    section, folding each row's single meeting into a `meetings` list —
    mirrors catalog.py's section-grouping, needed because
    section_meetings is one-to-many off sections (see CLAUDE.md's
    "Real day/time overlap logic (updated — section_meetings)").
    Preserves row order, so callers should ORDER BY section_id then a
    meeting-level column.
    """
    sections: dict[str, dict] = {}
    for r in rows:
        section_id = str(r["section_id"])
        course = sections.get(section_id)
        if course is None:
            course_id = str(r["course_id"])
            course = {
                "course_id": course_id,
                "code": r["code"],
                "title": r["title"],
                "credit_hours": r["credit_hours"],
                "category": categories.get(course_id, "major"),
                "section_id": section_id,
                "meetings": [],
                "is_locked": r["is_locked"],
                "is_flagged": r["is_flagged"],
                "flag_reason": r["flag_reason"],
            }
            sections[section_id] = course
        course["meetings"].append(
            {
                "days": r["days"],
                "start_time": r["start_time"].isoformat(),
                "end_time": r["end_time"].isoformat(),
            }
        )
    return list(sections.values())


@router.get("/me")
async def get_schedule(term: str, student: dict = Depends(get_current_student)) -> dict:
    student_id = str(student["id"])

    cached = await cache.get_cached_schedule(student_id, term)
    if cached is not None:
        return {"term": term, "courses": cached}

    pool = get_pool()
    rows = await pool.fetch(
        """
        select sp.section_id, sp.is_locked, sp.is_flagged, sp.flag_reason,
               c.id as course_id, c.code, c.title, c.credit_hours,
               sm.days, sm.start_time, sm.end_time
        from semester_plans sp
        join sections se on se.id = sp.section_id
        join section_meetings sm on sm.section_id = se.id
        join courses c on c.id = se.course_id
        where sp.student_id = $1 and sp.term = $2
        order by sp.section_id, sm.start_time
        """,
        student_id,
        term,
    )
    categories = await catalog.load_course_categories(pool, student_id)
    courses = _group_meetings_by_section([dict(r) for r in rows], categories)
    await cache.set_cached_schedule(student_id, term, courses)
    return {"term": term, "courses": courses}


@router.get("/me/plan")
async def get_full_plan(student: dict = Depends(get_current_student)) -> dict:
    """
    Every semester the student currently has a persisted plan for, not
    just one term — CLAUDE.md's GET /schedule/me?term= is explicitly
    per-term, but the dashboard's semester outlook row needs the whole
    plan at once. Added as its own endpoint rather than overloading
    GET /schedule/me's response shape when term is omitted, so existing
    callers of the per-term endpoint are unaffected. Not cached (unlike
    the per-term endpoint) — CLAUDE.md's caching spec is specifically
    per-term (schedule:{student_id}:{term}); an aggregate cache key
    isn't part of that spec, and this is already a single indexed query.
    """
    student_id = str(student["id"])
    pool = get_pool()

    rows = await pool.fetch(
        """
        select sp.term, sp.section_id, sp.is_locked, sp.is_flagged, sp.flag_reason,
               c.id as course_id, c.code, c.title, c.credit_hours,
               sm.days, sm.start_time, sm.end_time
        from semester_plans sp
        join sections se on se.id = sp.section_id
        join section_meetings sm on sm.section_id = se.id
        join courses c on c.id = se.course_id
        where sp.student_id = $1
        order by sp.term, sp.section_id, sm.start_time
        """,
        student_id,
    )
    categories = await catalog.load_course_categories(pool, student_id)

    rows_by_term: dict[str, list[dict]] = {}
    flags_by_term: dict[str, tuple[bool, str | None]] = {}
    for r in rows:
        term = r["term"]
        rows_by_term.setdefault(term, []).append(dict(r))
        if r["is_flagged"]:
            flags_by_term[term] = (True, r["flag_reason"])

    semesters = []
    for term, term_rows in rows_by_term.items():
        courses = _group_meetings_by_section(term_rows, categories)
        is_flagged, flag_reason = flags_by_term.get(term, (False, None))
        semesters.append(
            {
                "term": term,
                "is_flagged": is_flagged,
                "flag_reason": flag_reason,
                "courses": courses,
                "total_credits": sum(c["credit_hours"] for c in courses),
            }
        )

    ordered = sorted(semesters, key=lambda s: cascade.term_sort_key(s["term"]))
    return {"semesters": ordered}


@router.get("/me/projection")
async def get_projection(student: dict = Depends(get_current_student)) -> dict:
    """Graduation date estimate + credit hour summary (taken/in-progress/
    remaining), per CLAUDE.md. Reads persisted state only — doesn't
    trigger a solve."""
    student_id = str(student["id"])
    pool = get_pool()

    progress_rows = await pool.fetch(
        """
        select sp.status, c.credit_hours
        from student_progress sp
        join courses c on c.id = sp.course_id
        where sp.student_id = $1
        """,
        student_id,
    )
    credits_taken = sum(r["credit_hours"] for r in progress_rows if r["status"] == "done")
    credits_in_progress = sum(
        r["credit_hours"] for r in progress_rows if r["status"] == "in_progress"
    )

    remaining = await catalog.load_remaining_requirements(pool, student_id)
    credits_remaining = sum(rc.course.credit_hours for rc in remaining.values())

    total_credits = credits_taken + credits_in_progress + credits_remaining
    degree_percent = (
        round((credits_taken / total_credits) * 100, 1) if total_credits > 0 else 0.0
    )

    term_rows = await pool.fetch(
        "select distinct term from semester_plans where student_id = $1", student_id
    )
    projected_graduation = None
    if term_rows:
        latest_term = max(
            (r["term"] for r in term_rows), key=cascade.term_sort_key
        )
        season, year = latest_term.split()
        month = "December" if season == "Fall" else "May"
        projected_graduation = f"{month} {year}"

    return {
        "credits_taken": credits_taken,
        "credits_in_progress": credits_in_progress,
        "credits_remaining": credits_remaining,
        "degree_percent": degree_percent,
        "projected_graduation": projected_graduation,
    }
