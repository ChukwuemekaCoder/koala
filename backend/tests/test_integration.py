"""
Real end-to-end integration test: creates one throwaway test user via
Supabase's Auth Admin API (email_confirm=true — no live inbox needed,
unlike normal signup), then exercises POST /schedule/optimize,
GET /schedule/me, and POST /schedule/override through the real FastAPI
app against the real Supabase Postgres instance, through the real
auth.users FK chain. Cleans up afterward regardless of outcome.

Requires SUPABASE_SERVICE_ROLE_KEY and db/seed_test_catalog.sql applied.
Skipped automatically if the key isn't set (e.g. in CI before that
secret is configured), rather than failing the whole suite.
"""

import logging
from collections.abc import Coroutine
from typing import Any

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import cache
from app.config import settings
from app.db import close_pool, init_pool
from app.main import app

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    not settings.supabase_service_role_key,
    reason="SUPABASE_SERVICE_ROLE_KEY not set — skipping real integration test",
)

# CS structurally requires the Math minor (see db/seed_test_catalog.sql)
# — declaring both matches how this is actually meant to be used, and
# gives Fall's seeded sections enough non-conflicting credit capacity
# to reach a full course load (CS-only leaves too few Fall courses
# without an unmet prerequisite to hit the 12-credit floor).
CS_PROGRAM_ID = "aaaaaaaa-0000-0000-0000-000000000001"
MATH_PROGRAM_ID = "aaaaaaaa-0000-0000-0000-000000000002"
TEST_EMAIL = "koala-integration-test@oru.edu"
TEST_PASSWORD = "koala-test-password-CHANGE-1234!"

_admin_headers = {
    "apikey": settings.supabase_service_role_key or "",
    "Authorization": f"Bearer {settings.supabase_service_role_key}",
}


async def _create_test_user() -> str:
    async with httpx.AsyncClient(base_url=settings.supabase_url) as client:
        # In case a previous failed run left the user behind.
        await _delete_test_user_by_email(client)

        res = await client.post(
            "/auth/v1/admin/users",
            headers=_admin_headers,
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "email_confirm": True,
            },
        )
        res.raise_for_status()
        return res.json()["id"]


async def _delete_test_user_by_email(client: httpx.AsyncClient) -> None:
    res = await client.get(
        "/auth/v1/admin/users", headers=_admin_headers, params={"email": TEST_EMAIL}
    )
    if res.status_code != 200:
        return
    for user in res.json().get("users", []):
        if user["email"] == TEST_EMAIL:
            await client.delete(f"/auth/v1/admin/users/{user['id']}", headers=_admin_headers)


async def _delete_test_user(user_id: str) -> None:
    async with httpx.AsyncClient(base_url=settings.supabase_url) as client:
        res = await client.delete(f"/auth/v1/admin/users/{user_id}", headers=_admin_headers)
        res.raise_for_status()


async def _best_effort(description: str, coro: Coroutine[Any, Any, Any]) -> None:
    """
    Runs a teardown step without letting its failure stop the rest of
    teardown from running — logged loudly instead of raised, since a
    silent failure here (e.g. the Admin API delete not going through)
    would otherwise leave the test user behind with no signal that it
    happened.
    """
    try:
        await coro
    except Exception:
        logger.exception("Integration test teardown step failed: %s", description)


async def _sign_in() -> str:
    async with httpx.AsyncClient(base_url=settings.supabase_url) as client:
        res = await client.post(
            "/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": settings.supabase_anon_key},
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        res.raise_for_status()
        return res.json()["access_token"]


@pytest_asyncio.fixture
async def test_user(db_pool):
    user_id = await _create_test_user()
    try:
        yield user_id
    finally:
        # Each step runs independently — one failing (e.g. a transient
        # DB hiccup on the first delete) must not skip the rest,
        # especially the auth user deletion.
        await _best_effort(
            "delete semester_plans",
            db_pool.execute(
                "delete from semester_plans where student_id = $1", user_id
            ),
        )
        await _best_effort(
            "delete student_programs",
            db_pool.execute(
                "delete from student_programs where student_id = $1", user_id
            ),
        )
        await _best_effort(
            "delete students",
            db_pool.execute("delete from students where id = $1", user_id),
        )
        await _best_effort("delete auth user", _delete_test_user(user_id))


@pytest.mark.asyncio
async def test_optimize_get_and_override_end_to_end(db_pool, test_user):
    user_id = test_user
    access_token = await _sign_in()
    headers = {"Authorization": f"Bearer {access_token}"}

    await init_pool()
    cache.init_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as api:
            # Real signup-completion call, through the real auth pipeline.
            create_res = await api.post(
                "/students/me",
                json={"first_name": "Koala", "last_name": "Tester"},
                headers=headers,
            )
            assert create_res.status_code == 201
            assert create_res.json()["id"] == user_id

            # No POST /students/me/programs endpoint exists yet (out of
            # scope — see plan) — declare CS + its required Math minor
            # directly for this real, FK-backed student.
            await db_pool.executemany(
                "insert into student_programs (student_id, program_id) values ($1, $2)",
                [(user_id, CS_PROGRAM_ID), (user_id, MATH_PROGRAM_ID)],
            )

            optimize_res = await api.post("/schedule/optimize", headers=headers)
            assert optimize_res.status_code == 200
            plan = optimize_res.json()
            assert len(plan["semesters"]) > 0
            first_semester = plan["semesters"][0]
            assert first_semester["feasible"] is True
            assert first_semester["total_credits"] >= 12
            first_term = first_semester["term"]
            optimized_course_ids = {c["course_id"] for c in first_semester["courses"]}

            # GET /schedule/me should return exactly what optimize persisted.
            get_res = await api.get(
                "/schedule/me", params={"term": first_term}, headers=headers
            )
            assert get_res.status_code == 200
            fetched_course_ids = {c["course_id"] for c in get_res.json()["courses"]}
            assert fetched_course_ids == optimized_course_ids

            # Second GET should be a cache hit — same result either way.
            get_res_2 = await api.get(
                "/schedule/me", params={"term": first_term}, headers=headers
            )
            assert get_res_2.json() == get_res.json()

            # Override: remove one course from the first semester.
            course_to_remove = first_semester["courses"][0]["course_id"]
            override_res = await api.post(
                "/schedule/override",
                json={"term": first_term, "remove_course_id": course_to_remove},
                headers=headers,
            )
            # Either it applies (200) or correctly blocks for dropping
            # below the 12-credit floor (422) — both are valid outcomes
            # depending on what optimize happened to produce.
            assert override_res.status_code in (200, 422)

            if override_res.status_code == 200:
                new_plan = override_res.json()
                new_course_ids = {
                    c["course_id"] for c in new_plan["semesters"][0]["courses"]
                }
                assert course_to_remove not in new_course_ids

                # Cache must have been invalidated by the override — a
                # fresh GET should reflect the new state, not the old.
                get_res_3 = await api.get(
                    "/schedule/me", params={"term": first_term}, headers=headers
                )
                assert course_to_remove not in {
                    c["course_id"] for c in get_res_3.json()["courses"]
                }
    finally:
        await cache.close_client()
        await close_pool()
