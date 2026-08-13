"""
HTTP contract tests for the catalog read endpoints (GET /programs,
GET /courses, GET /courses/{id}/sections) via FastAPI
dependency_overrides — no real Supabase auth needed since every one of
these is a read-only SELECT against seeded catalog data, safe for a
fake student_id (see test_students_endpoints.py's docstring for the
same reasoning). Uses the fixed UUIDs from db/seed_test_catalog.sql.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import cache
from app.auth import get_current_student
from app.db import close_pool, init_pool
from app.main import app

FAKE_STUDENT = {
    "id": uuid.uuid4(),
    "email": "fake-student@oru.edu",
    "first_name": "Fake",
    "last_name": "Student",
    "class_standing": None,
    "current_term": None,
    "has_completed_tutorial": False,
    "onboarding_completed_at": None,
}

CS110 = "bbbbbbbb-0000-0000-0000-000000000001"
ART100 = "bbbbbbbb-0000-0000-0000-000000000009"


@pytest_asyncio.fixture
async def client():
    await init_pool()
    cache.init_client()
    app.dependency_overrides[get_current_student] = lambda: FAKE_STUDENT
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await cache.close_client()
    await close_pool()


@pytest.mark.asyncio
async def test_list_programs_includes_seeded_programs(client):
    res = await client.get("/programs")
    assert res.status_code == 200
    names = {p["name"] for p in res.json()["programs"]}
    assert "Computer Science (TEST)" in names
    assert "Mathematics (TEST)" in names


@pytest.mark.asyncio
async def test_list_programs_exposes_required_by_for_auto_add(client):
    res = await client.get("/programs")
    math = next(p for p in res.json()["programs"] if p["name"] == "Mathematics (TEST)")
    cs = next(p for p in res.json()["programs"] if p["name"] == "Computer Science (TEST)")
    assert math["required_by_program_id"] == cs["id"]
    assert cs["required_by_program_id"] is None


@pytest.mark.asyncio
async def test_list_courses_includes_seeded_courses(client):
    res = await client.get("/courses")
    assert res.status_code == 200
    ids = {c["id"] for c in res.json()["courses"]}
    assert CS110 in ids


@pytest.mark.asyncio
async def test_course_sections_requires_term(client):
    res = await client.get(f"/courses/{CS110}/sections")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_course_sections_returns_no_seat_data(client):
    res = await client.get(f"/courses/{ART100}/sections", params={"term": "Fall 2026"})
    assert res.status_code == 200
    sections = res.json()["sections"]
    assert len(sections) >= 1
    for section in sections:
        assert "seats_total" not in section
        assert "seats_taken" not in section
        assert section["meetings"]  # every section has at least one meeting


@pytest.mark.asyncio
async def test_course_sections_groups_multi_meeting_section(client):
    # ART100's conflicting section (see db/seed_test_catalog.sql) has
    # two meetings (MW + a standalone Friday) — must come back as one
    # section with 2 meetings, not two separate section entries.
    res = await client.get(f"/courses/{ART100}/sections", params={"term": "Fall 2026"})
    sections = res.json()["sections"]
    meeting_counts = sorted(len(s["meetings"]) for s in sections)
    assert meeting_counts == [1, 2]
