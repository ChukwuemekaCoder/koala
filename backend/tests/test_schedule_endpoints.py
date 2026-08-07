"""
HTTP contract tests via FastAPI dependency_overrides — no real Supabase
auth involved. Covers error paths that never reach a semester_plans
write, so a fake (non-existent) student_id is safe: every query hit
before those errors raise is a read-only SELECT, and FK constraints are
only enforced on writes. The real happy-path (a write through the real
auth.users FK chain) is covered separately in test_integration.py.
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
async def test_optimize_422_when_no_declared_programs(client):
    res = await client.post("/schedule/optimize")
    assert res.status_code == 422
    assert "declare" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_override_422_when_neither_field_set(client):
    res = await client.post("/schedule/override", json={"term": "Fall 2026"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_override_404_when_removing_course_not_in_plan(client):
    res = await client.post(
        "/schedule/override",
        json={"term": "Fall 2026", "remove_course_id": str(uuid.uuid4())},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_override_404_when_adding_nonexistent_section(client):
    res = await client.post(
        "/schedule/override",
        json={"term": "Fall 2026", "add_section_id": str(uuid.uuid4())},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_schedule_empty_when_no_plan_exists(client):
    res = await client.get("/schedule/me", params={"term": "Fall 2026"})
    assert res.status_code == 200
    assert res.json() == {"term": "Fall 2026", "courses": []}


@pytest.mark.asyncio
async def test_get_full_plan_empty_when_no_plan_exists(client):
    res = await client.get("/schedule/me/plan")
    assert res.status_code == 200
    assert res.json() == {"semesters": []}


@pytest.mark.asyncio
async def test_get_projection_zeros_when_nothing_declared_or_planned(client):
    res = await client.get("/schedule/me/projection")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "credits_taken": 0,
        "credits_in_progress": 0,
        "credits_remaining": 0,
        "degree_percent": 0.0,
        "projected_graduation": None,
    }
