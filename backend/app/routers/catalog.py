from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_student
from app.db import get_pool
from app.serialization import group_meetings_by_section

router = APIRouter(tags=["catalog"])


@router.get("/programs")
async def list_programs(student: dict = Depends(get_current_student)) -> dict:
    """Every major/minor in the catalog — powers onboarding step 1's
    program search (and, via required_by_program_id, the client-side
    "auto-add the required minor" check)."""
    rows = await get_pool().fetch(
        "select id, name, type, department, required_by_program_id "
        "from programs order by type, name"
    )
    return {
        "programs": [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "type": r["type"],
                "department": r["department"],
                "required_by_program_id": (
                    str(r["required_by_program_id"])
                    if r["required_by_program_id"]
                    else None
                ),
            }
            for r in rows
        ]
    }


@router.get("/courses")
async def list_courses(student: dict = Depends(get_current_student)) -> dict:
    """Every course in the catalog, no student-specific status or
    category — see GET /students/me/course-history for the onboarding-
    step-3 shaped version of this."""
    rows = await get_pool().fetch(
        "select id, code, title, credit_hours, offering_frequency, department "
        "from courses order by code"
    )
    return {
        "courses": [
            {
                "id": str(r["id"]),
                "code": r["code"],
                "title": r["title"],
                "credit_hours": r["credit_hours"],
                "offering_frequency": r["offering_frequency"],
                "department": r["department"],
            }
            for r in rows
        ]
    }


@router.get("/courses/{course_id}/sections")
async def list_course_sections(
    course_id: str, term: str | None = None, student: dict = Depends(get_current_student)
) -> dict:
    """Every section of this course in the given term, each with its
    meetings — powers the override modal's "current + alternative
    sections" radio list. No seat data (see CLAUDE.md's "No seat
    capacity tracking")."""
    if not term:
        raise HTTPException(400, "term is required")

    rows = await get_pool().fetch(
        """
        select se.id as section_id, sm.days, sm.start_time, sm.end_time
        from sections se
        join section_meetings sm on sm.section_id = se.id
        where se.course_id = $1 and se.term = $2
        order by se.id, sm.start_time
        """,
        course_id,
        term,
    )
    meetings_by_section = group_meetings_by_section(
        [dict(r) for r in rows]
    )
    return {
        "sections": [
            {"section_id": section_id, "meetings": meetings}
            for section_id, meetings in meetings_by_section.items()
        ]
    }
