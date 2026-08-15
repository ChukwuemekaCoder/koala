from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import cache
from app.auth import AuthClaims, get_current_auth_user, get_current_student
from app.db import get_pool
from app.routers.schedule import (
    _cleanup_orphaned_terms,
    _persist_cascade_result,
    _serialize_cascade,
)
from app.solver import cascade, catalog

router = APIRouter(prefix="/students/me", tags=["students"])


def _serialize_student(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "class_standing": row["class_standing"],
        "current_term": row["current_term"],
        "has_completed_tutorial": row["has_completed_tutorial"],
        "onboarding_complete": row["onboarding_completed_at"] is not None,
    }


class CreateStudentRequest(BaseModel):
    first_name: str
    last_name: str


@router.post("", status_code=201)
async def create_me(
    body: CreateStudentRequest,
    auth: AuthClaims = Depends(get_current_auth_user),
) -> dict:
    # Idempotent: a retried call (double network request, re-triggered
    # verification) returns the existing row instead of erroring, since
    # this is meant to be called exactly once per account in practice.
    row = await get_pool().fetchrow(
        """
        insert into students (id, email, first_name, last_name)
        values ($1, $2, $3, $4)
        on conflict (id) do nothing
        returning *
        """,
        auth.user_id,
        auth.email,
        body.first_name,
        body.last_name,
    )
    if row is None:
        row = await get_pool().fetchrow(
            "select * from students where id = $1", auth.user_id
        )
    return _serialize_student(dict(row))


@router.get("")
async def get_me(student: dict = Depends(get_current_student)) -> dict:
    return _serialize_student(student)


ClassStanding = Literal["freshman", "sophomore", "junior", "senior"]
CurrentTerm = Literal["fall", "spring"]


class UpdateStudentRequest(BaseModel):
    class_standing: ClassStanding | None = None
    current_term: CurrentTerm | None = None
    has_completed_tutorial: bool | None = None


@router.patch("")
async def update_me(
    body: UpdateStudentRequest, student: dict = Depends(get_current_student)
) -> dict:
    """Onboarding step 2. Both fields are optional per-call (either can
    be set independently), but the onboarding UI submits both together.
    Only touches the fields actually provided — omitting one leaves it
    unchanged rather than nulling it out."""
    student_id = str(student["id"])
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return _serialize_student(student)

    set_clauses = [f"{field} = ${i + 2}" for i, field in enumerate(updates)]
    row = await get_pool().fetchrow(
        f"update students set {', '.join(set_clauses)} where id = $1 returning *",
        student_id,
        *updates.values(),
    )
    return _serialize_student(dict(row))


class ProgramDeclaration(BaseModel):
    program_id: str
    priority_rank: int | None = Field(default=None, gt=0)


class DeclareProgramsRequest(BaseModel):
    programs: list[ProgramDeclaration]


def _serialize_declared_program(row: dict) -> dict:
    return {
        "program_id": str(row["program_id"]),
        "name": row["name"],
        "type": row["type"],
        "priority_rank": row["priority_rank"],
    }


async def _fetch_declared_programs(student_id: str) -> list[dict]:
    rows = await get_pool().fetch(
        """
        select sp.program_id, sp.priority_rank, p.name, p.type
        from student_programs sp
        join programs p on p.id = sp.program_id
        where sp.student_id = $1
        order by p.type, p.name
        """,
        student_id,
    )
    return [_serialize_declared_program(dict(r)) for r in rows]


@router.post("/programs")
async def declare_programs(
    body: DeclareProgramsRequest, student: dict = Depends(get_current_student)
) -> dict:
    """
    Onboarding step 1. Replaces the student's full set of declared
    programs with exactly what's submitted here — the UI collects the
    whole multi-select selection at once, so this mirrors that: an empty
    list clears all declarations, a resubmission after the student
    changes their mind fully replaces the previous set rather than
    merging with it.
    """
    student_id = str(student["id"])
    pool = get_pool()

    program_ids = [p.program_id for p in body.programs]
    if program_ids:
        rows = await pool.fetch(
            "select id from programs where id = any($1::uuid[])", program_ids
        )
        valid_ids = {str(r["id"]) for r in rows}
        invalid_ids = set(program_ids) - valid_ids
        if invalid_ids:
            raise HTTPException(
                422, f"Unknown program id(s): {', '.join(sorted(invalid_ids))}"
            )

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            "delete from student_programs where student_id = $1", student_id
        )
        for p in body.programs:
            await conn.execute(
                """
                insert into student_programs (student_id, program_id, priority_rank)
                values ($1, $2, $3)
                """,
                student_id,
                p.program_id,
                p.priority_rank,
            )

    return {"programs": await _fetch_declared_programs(student_id)}


@router.get("/programs")
async def get_declared_programs(student: dict = Depends(get_current_student)) -> dict:
    """Currently declared majors/minors — onboarding step 1's re-hydration
    source when a student navigates Back to it after already declaring.
    Empty list is a valid response (nothing declared yet), not an error."""
    return {"programs": await _fetch_declared_programs(str(student["id"]))}


ProgressStatus = Literal["done", "in_progress", "not_taken"]


class ProgressEntry(BaseModel):
    course_id: str
    status: ProgressStatus


class BulkProgressRequest(BaseModel):
    progress: list[ProgressEntry]


def _serialize_progress(row: dict) -> dict:
    return {
        "course_id": str(row["course_id"]),
        "code": row["code"],
        "title": row["title"],
        "status": row["status"],
    }


async def _fetch_progress(student_id: str) -> list[dict]:
    rows = await get_pool().fetch(
        """
        select sp.course_id, sp.status, c.code, c.title
        from student_progress sp
        join courses c on c.id = sp.course_id
        where sp.student_id = $1
        order by c.code
        """,
        student_id,
    )
    return [_serialize_progress(dict(r)) for r in rows]


async def _validate_course_ids(course_ids: list[str]) -> None:
    if not course_ids:
        return
    rows = await get_pool().fetch(
        "select id from courses where id = any($1::uuid[])", course_ids
    )
    valid_ids = {str(r["id"]) for r in rows}
    invalid_ids = set(course_ids) - valid_ids
    if invalid_ids:
        raise HTTPException(
            422, f"Unknown course id(s): {', '.join(sorted(invalid_ids))}"
        )


@router.post("/progress")
async def bulk_confirm_progress(
    body: BulkProgressRequest, student: dict = Depends(get_current_student)
) -> dict:
    """
    Onboarding step 3. A course confirmed once satisfies every program
    requirement it applies to — student_progress has exactly one row per
    student-course (enforced by its own unique constraint), never one
    per requirement, so a plain upsert here is already correct; there's
    nothing extra to do to honor "confirm once, applies everywhere"
    beyond not accidentally keying anything by program.
    """
    student_id = str(student["id"])
    pool = get_pool()

    if not body.progress:
        raise HTTPException(422, "Provide at least one course status to confirm")

    await _validate_course_ids([p.course_id for p in body.progress])

    async with pool.acquire() as conn, conn.transaction():
        await conn.executemany(
            """
            insert into student_progress (student_id, course_id, status, updated_at)
            values ($1, $2, $3, now())
            on conflict (student_id, course_id) do update
                set status = excluded.status, updated_at = excluded.updated_at
            """,
            [(student_id, p.course_id, p.status) for p in body.progress],
        )
        # Onboarding step 3 completing is what marks onboarding done.
        # coalesce so a later re-run of this endpoint doesn't overwrite
        # the original completion timestamp.
        await conn.execute(
            """
            update students
            set onboarding_completed_at = coalesce(onboarding_completed_at, now())
            where id = $1
            """,
            student_id,
        )

    return {"progress": await _fetch_progress(student_id)}


class ProgressUpdateRequest(BaseModel):
    status: ProgressStatus


@router.patch("/progress/{course_id}")
async def correct_progress(
    course_id: str,
    body: ProgressUpdateRequest,
    student: dict = Depends(get_current_student),
) -> dict:
    """
    Single-course retroactive correction — re-solve cascade entry point
    B. Unlike POST /schedule/override's blast-radius-only re-solve, this
    re-solves ALL uncommitted future semesters from the student's current
    term forward (per CLAUDE.md: a progress correction can shift the
    whole remaining-requirements pool, not just one course's slot). Past/
    completed semesters are never touched, since resolve_from_term only
    ever walks forward from start_term.
    """
    student_id = str(student["id"])
    pool = get_pool()

    await _validate_course_ids([course_id])

    await pool.execute(
        """
        insert into student_progress (student_id, course_id, status, updated_at)
        values ($1, $2, $3, now())
        on conflict (student_id, course_id) do update
            set status = excluded.status, updated_at = excluded.updated_at
        """,
        student_id,
        course_id,
        body.status,
    )

    start_term = cascade.current_term_label(student.get("current_term"))
    result = await cascade.resolve_from_term(pool, student_id, start_term)
    await _persist_cascade_result(student_id, result)
    await _cleanup_orphaned_terms(student_id, {s.term for s in result.semesters})
    await cache.invalidate_schedule_cache(student_id)

    return _serialize_cascade(result)


@router.get("/course-history")
async def get_course_history(student: dict = Depends(get_current_student)) -> dict:
    """
    Onboarding step 3: every course required by the student's declared
    programs (whatever their current status), each annotated with the
    same category label the dashboard's calendar grid uses and the
    student's current status (defaulting to 'not_taken' when they
    haven't confirmed it yet). One call gives the frontend everything
    the course-history list + category filter + Done/In-progress tags
    need — declared programs must exist first (422s otherwise, same
    gate as POST /schedule/optimize).
    """
    student_id = str(student["id"])
    pool = get_pool()

    required = await catalog.load_all_required_courses(pool, student_id)
    if not required:
        raise HTTPException(
            422, "Declare at least one major or minor before confirming course history"
        )
    categories = catalog.categories_from_remaining(required)

    progress_rows = await pool.fetch(
        "select course_id, status from student_progress where student_id = $1",
        student_id,
    )
    status_by_course = {str(r["course_id"]): r["status"] for r in progress_rows}

    courses = [
        {
            "course_id": course_id,
            "code": rc.course.code,
            "title": rc.course.title,
            "credit_hours": rc.course.credit_hours,
            "category": categories.get(course_id, "major"),
            "status": status_by_course.get(course_id, "not_taken"),
        }
        for course_id, rc in required.items()
    ]
    courses.sort(key=lambda c: c["code"])
    return {"courses": courses}
