"""
Real end-to-end integration test: creates one throwaway test user via
Supabase's Auth Admin API (email_confirm=true — no live inbox needed,
unlike normal signup), then walks the real onboarding flow (declare
programs, bulk-confirm progress) through POST /schedule/optimize,
GET /schedule/me, POST /schedule/override, and
PATCH /students/me/progress/{course_id} (cascade entry point B) —
through the real FastAPI app against the real Supabase Postgres
instance, through the real auth.users FK chain. Cleans up afterward
regardless of outcome.

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
CS110_ID = "bbbbbbbb-0000-0000-0000-000000000001"
CS210_ID = "bbbbbbbb-0000-0000-0000-000000000002"
THEO101_ID = "bbbbbbbb-0000-0000-0000-000000000006"
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
async def test_optimize_get_and_override_end_to_end(test_user):
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

            # Onboarding step 1: declare CS + its required Math minor
            # through the real endpoint (validates against the real
            # programs catalog).
            declare_res = await api.post(
                "/students/me/programs",
                json={
                    "programs": [
                        {"program_id": CS_PROGRAM_ID},
                        {"program_id": MATH_PROGRAM_ID},
                    ]
                },
                headers=headers,
            )
            assert declare_res.status_code == 200
            declared_ids = {p["program_id"] for p in declare_res.json()["programs"]}
            assert declared_ids == {CS_PROGRAM_ID, MATH_PROGRAM_ID}

            # Onboarding Back re-hydration source: a fresh GET (not just
            # the POST's own echoed response) must reflect what was just
            # declared — this is what ProgramSelectStep re-fetches when a
            # student navigates Back to step 1.
            get_declared_res = await api.get("/students/me/programs", headers=headers)
            assert get_declared_res.status_code == 200
            get_declared_ids = {p["program_id"] for p in get_declared_res.json()["programs"]}
            assert get_declared_ids == {CS_PROGRAM_ID, MATH_PROGRAM_ID}

            # Onboarding step 2: confirm class standing + current term
            # through the real endpoint — there was previously no way
            # to set these at all.
            standing_res = await api.patch(
                "/students/me",
                json={"class_standing": "freshman", "current_term": "fall"},
                headers=headers,
            )
            assert standing_res.status_code == 200
            assert standing_res.json()["class_standing"] == "freshman"
            assert standing_res.json()["current_term"] == "fall"

            # Catalog reads: generic, not student-specific, but confirm
            # they actually return the real seeded catalog through the
            # real endpoints.
            programs_res = await api.get("/programs", headers=headers)
            assert programs_res.status_code == 200
            assert any(
                p["id"] == CS_PROGRAM_ID for p in programs_res.json()["programs"]
            )
            courses_res = await api.get("/courses", headers=headers)
            assert courses_res.status_code == 200
            assert any(c["id"] == CS110_ID for c in courses_res.json()["courses"])

            # Course history before any progress is confirmed: every
            # course required by the declared CS+Math pool, all
            # defaulting to not_taken since nothing's been confirmed yet.
            history_before = await api.get("/students/me/course-history", headers=headers)
            assert history_before.status_code == 200
            history_by_id = {c["course_id"]: c for c in history_before.json()["courses"]}
            assert CS110_ID in history_by_id
            assert history_by_id[CS110_ID]["status"] == "not_taken"

            # Onboarding step 3: bulk-confirm course history. CS110 marked
            # done should be excluded from the generated plan entirely;
            # THEO101 as not_taken exercises a second entry in the same
            # bulk call without affecting scheduling.
            progress_res = await api.post(
                "/students/me/progress",
                json={
                    "progress": [
                        {"course_id": CS110_ID, "status": "done"},
                        {"course_id": THEO101_ID, "status": "not_taken"},
                    ]
                },
                headers=headers,
            )
            assert progress_res.status_code == 200
            progress_course_ids = {p["course_id"] for p in progress_res.json()["progress"]}
            assert progress_course_ids == {CS110_ID, THEO101_ID}

            # Course history after confirming: load_all_required_courses
            # (unlike load_remaining_requirements) must still include
            # CS110 even though it's now 'done' — this is the real proof
            # exclude_completed=False actually differs from the default,
            # which a fake-student unit test can't demonstrate (no real
            # student_progress row to exclude in the first place).
            history_after = await api.get("/students/me/course-history", headers=headers)
            assert history_after.status_code == 200
            history_by_id_after = {
                c["course_id"]: c for c in history_after.json()["courses"]
            }
            assert history_by_id_after[CS110_ID]["status"] == "done"
            assert history_by_id_after[THEO101_ID]["status"] == "not_taken"

            # Bulk progress confirmation completing is what marks
            # onboarding done (CLAUDE.md: set on step 3, not step 1).
            me_res = await api.get("/students/me", headers=headers)
            assert me_res.status_code == 200
            assert me_res.json()["onboarding_complete"] is True
            assert me_res.json()["has_completed_tutorial"] is False

            # Tutorial overlay dismissal (Skip or completing all 4 slides)
            # persists via this PATCH — never client-side storage
            # (CLAUDE.md) — so it must survive a fresh GET, not just
            # reflect back in the PATCH response itself.
            tutorial_res = await api.patch(
                "/students/me", json={"has_completed_tutorial": True}, headers=headers
            )
            assert tutorial_res.status_code == 200
            assert tutorial_res.json()["has_completed_tutorial"] is True
            me_res_after_tutorial = await api.get("/students/me", headers=headers)
            assert me_res_after_tutorial.json()["has_completed_tutorial"] is True

            # Optimize's 422 gate is "has declared programs" — the thing
            # this whole endpoint suite was blocked on until now, since
            # there was previously no real endpoint to declare them
            # through. Confirm it succeeds via the real onboarding path,
            # not just via a direct-SQL workaround.
            optimize_res = await api.post("/schedule/optimize", headers=headers)
            assert optimize_res.status_code == 200
            plan = optimize_res.json()
            assert len(plan["semesters"]) > 0
            first_semester = plan["semesters"][0]
            assert first_semester["feasible"] is True
            assert first_semester["total_credits"] >= 12
            first_term = first_semester["term"]
            optimized_course_ids = {c["course_id"] for c in first_semester["courses"]}

            # CS110 was marked 'done' — it must not appear anywhere in
            # the generated plan, in any semester.
            all_plan_course_ids = {
                c["course_id"]
                for semester in plan["semesters"]
                for c in semester["courses"]
            }
            assert CS110_ID not in all_plan_course_ids

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

            # GET /schedule/me/plan should return every semester optimize
            # persisted, not just one term — this is the endpoint the
            # dashboard's semester outlook row actually needs, which
            # didn't exist before this stage.
            full_plan_res = await api.get("/schedule/me/plan", headers=headers)
            assert full_plan_res.status_code == 200
            full_plan = full_plan_res.json()
            assert {s["term"] for s in full_plan["semesters"]} == {
                s["term"] for s in plan["semesters"]
            }
            assert full_plan["semesters"] == sorted(
                full_plan["semesters"], key=lambda s: s["term"] != first_term
            )  # first_term (chronologically earliest) sorts first
            for course in full_plan["semesters"][0]["courses"]:
                assert course["category"] in ("major", "minor", "gen_ed")

            # GET /schedule/me/projection: CS110 (3cr) marked done is the
            # only real completion so far; declared CS+Math's full
            # requirement pool is exactly 28 credits across 8 courses
            # (db/seed_test_catalog.sql), so remaining = 28 - 3 = 25.
            projection_res = await api.get("/schedule/me/projection", headers=headers)
            assert projection_res.status_code == 200
            projection = projection_res.json()
            assert projection["credits_taken"] == 3
            assert projection["credits_in_progress"] == 0
            assert projection["credits_remaining"] == 25
            assert projection["degree_percent"] == round(3 / 28 * 100, 1)
            assert projection["projected_graduation"] is not None
            assert any(
                projection["projected_graduation"].startswith(month)
                for month in ("May", "December")
            )

            # Add-a-course modal's data source: the full 3-semester plan
            # already covers every remaining CS+Math course, so nothing
            # should be addable to any term right now — proves
            # load_addable_candidates' "excludes anything scheduled
            # anywhere" logic against real data, not just an empty pool.
            addable_res = await api.get(
                "/schedule/me/addable", params={"term": first_term}, headers=headers
            )
            assert addable_res.status_code == 200
            assert addable_res.json()["courses"] == []

            # Attempting to add CS210's already-scheduled section into a
            # DIFFERENT term than where it's actually scheduled must be
            # blocked — otherwise the same requirement would be
            # double-booked across two semesters.
            cs210_term = next(
                semester["term"]
                for semester in full_plan["semesters"]
                if any(c["course_id"] == CS210_ID for c in semester["courses"])
            )
            cs210_section_id = next(
                c["section_id"]
                for semester in full_plan["semesters"]
                for c in semester["courses"]
                if c["course_id"] == CS210_ID
            )
            other_term = next(
                semester["term"]
                for semester in full_plan["semesters"]
                if semester["term"] != cs210_term
            )
            double_book_res = await api.post(
                "/schedule/override",
                json={"term": other_term, "add_section_id": cs210_section_id},
                headers=headers,
            )
            assert double_book_res.status_code == 422
            assert "already scheduled" in double_book_res.json()["detail"].lower()

            # Override modal's data source: list this course's sections
            # for the term before deciding to remove/swap it.
            course_to_remove = first_semester["courses"][0]["course_id"]
            sections_res = await api.get(
                f"/courses/{course_to_remove}/sections",
                params={"term": first_term},
                headers=headers,
            )
            assert sections_res.status_code == 200
            assert len(sections_res.json()["sections"]) >= 1

            # Override: remove one course from the first semester.
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

            # Retroactive correction (cascade entry point B): mark CS210
            # done directly via PATCH, as if the student forgot to record
            # it earlier — CLAUDE.md's own example for this trigger. This
            # re-solves ALL future uncommitted semesters from the current
            # term forward (not just the override's narrower blast
            # radius), so CS210 must disappear from wherever it now
            # would have been scheduled.
            patch_res = await api.patch(
                f"/students/me/progress/{CS210_ID}",
                json={"status": "done"},
                headers=headers,
            )
            assert patch_res.status_code == 200
            corrected_plan = patch_res.json()
            corrected_course_ids = {
                c["course_id"]
                for semester in corrected_plan["semesters"]
                for c in semester["courses"]
            }
            assert CS210_ID not in corrected_course_ids

            # And the correction is visible through the read path too.
            for semester in corrected_plan["semesters"]:
                get_after_patch = await api.get(
                    "/schedule/me", params={"term": semester["term"]}, headers=headers
                )
                assert CS210_ID not in {
                    c["course_id"] for c in get_after_patch.json()["courses"]
                }
    finally:
        await cache.close_client()
        await close_pool()
