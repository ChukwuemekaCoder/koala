"""
HTTP contract tests for the onboarding endpoints via FastAPI
dependency_overrides — no real Supabase auth. Same reasoning as
test_schedule_endpoints.py: every case here is either a read-only SELECT
or a validation failure that never reaches a students/auth.users-FK'd
write, so a fake student_id is safe. Real writes through the real FK
chain are covered by test_integration.py.
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
async def test_declare_programs_rejects_unknown_program_id(client):
    res = await client.post(
        "/students/me/programs",
        json={"programs": [{"program_id": str(uuid.uuid4())}]},
    )
    assert res.status_code == 422
    assert "unknown program" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_declare_programs_empty_list_is_allowed(client):
    # An empty declaration is valid at this layer (clears selections) —
    # /schedule/optimize is what enforces "at least one" downstream.
    res = await client.post("/students/me/programs", json={"programs": []})
    assert res.status_code == 200
    assert res.json() == {"programs": []}


@pytest.mark.asyncio
async def test_get_declared_programs_empty_when_none_declared(client):
    # Read-only, so safe against FAKE_STUDENT's nonexistent id — nothing
    # declared is a valid response, not an error, same as the POST case.
    res = await client.get("/students/me/programs")
    assert res.status_code == 200
    assert res.json() == {"programs": []}


@pytest.mark.asyncio
async def test_declare_programs_rejects_non_positive_priority_rank(client):
    res = await client.post(
        "/students/me/programs",
        json={
            "programs": [{"program_id": str(uuid.uuid4()), "priority_rank": 0}]
        },
    )
    assert res.status_code == 422  # Pydantic's gt=0 catches this before any query


@pytest.mark.asyncio
async def test_bulk_progress_requires_at_least_one_entry(client):
    res = await client.post("/students/me/progress", json={"progress": []})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_bulk_progress_rejects_unknown_course_id(client):
    res = await client.post(
        "/students/me/progress",
        json={"progress": [{"course_id": str(uuid.uuid4()), "status": "done"}]},
    )
    assert res.status_code == 422
    assert "unknown course" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bulk_progress_rejects_invalid_status_value(client):
    res = await client.post(
        "/students/me/progress",
        json={
            "progress": [
                {"course_id": str(uuid.uuid4()), "status": "not-a-real-status"}
            ]
        },
    )
    assert res.status_code == 422  # Pydantic's Literal catches this before any query


@pytest.mark.asyncio
async def test_patch_progress_rejects_unknown_course_id(client):
    fake_course_id = str(uuid.uuid4())
    res = await client.patch(
        f"/students/me/progress/{fake_course_id}", json={"status": "done"}
    )
    assert res.status_code == 422
    assert "unknown course" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_progress_rejects_invalid_status_value(client):
    fake_course_id = str(uuid.uuid4())
    res = await client.patch(
        f"/students/me/progress/{fake_course_id}",
        json={"status": "not-a-real-status"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_me_rejects_invalid_class_standing(client):
    res = await client.patch("/students/me", json={"class_standing": "not-a-real-year"})
    assert res.status_code == 422  # Pydantic's Literal catches this before any query


@pytest.mark.asyncio
async def test_patch_me_rejects_invalid_current_term(client):
    res = await client.patch("/students/me", json={"current_term": "summer"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_me_with_no_fields_is_a_no_op(client):
    res = await client.patch("/students/me", json={})
    assert res.status_code == 200
    assert res.json()["id"] == str(FAKE_STUDENT["id"])


@pytest.mark.asyncio
async def test_course_history_422_when_no_declared_programs(client):
    res = await client.get("/students/me/course-history")
    assert res.status_code == 422
    assert "declare" in res.json()["detail"].lower()
