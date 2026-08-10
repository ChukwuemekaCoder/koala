"""
Tests catalog.py against the real Postgres instance, using the fixed
UUIDs from db/seed_test_catalog.sql. Run that seed script first.

Safe without any real student: every query here is read-only, and a
syntactically-valid but non-existent student_id never violates an FK
(FKs are only enforced on writes). See catalog.py's
_remaining_requirements_for_declared_programs docstring.
"""

import uuid

import pytest

from app.solver.catalog import (
    PrerequisiteCycleError,
    _check_for_cycles,
    _remaining_requirements_for_declared_programs,
    categories_from_remaining,
    load_locked_candidates,
    load_term_candidates,
)
from app.solver.scheduler_backtracking_sketch import TIER_GENED, TIER_MAJOR, TIER_MINOR

CS = "aaaaaaaa-0000-0000-0000-000000000001"
MATH = "aaaaaaaa-0000-0000-0000-000000000002"
ART = "aaaaaaaa-0000-0000-0000-000000000003"

CS110 = "bbbbbbbb-0000-0000-0000-000000000001"
CS210 = "bbbbbbbb-0000-0000-0000-000000000002"
CS310 = "bbbbbbbb-0000-0000-0000-000000000003"
MATH120 = "bbbbbbbb-0000-0000-0000-000000000004"
MATH121 = "bbbbbbbb-0000-0000-0000-000000000005"
THEO101 = "bbbbbbbb-0000-0000-0000-000000000006"
ENGL101 = "bbbbbbbb-0000-0000-0000-000000000007"
HIST101 = "bbbbbbbb-0000-0000-0000-000000000008"
ART100 = "bbbbbbbb-0000-0000-0000-000000000009"
ART200 = "bbbbbbbb-0000-0000-0000-000000000010"

FAKE_STUDENT_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_cs_only_pulls_cs_requirements_not_other_programs(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    ids = set(remaining.keys())
    assert ids == {CS110, CS210, CS310, MATH121, THEO101, ENGL101, HIST101}
    assert MATH120 not in ids  # only required by the Math minor, not declared
    assert ART100 not in ids


@pytest.mark.asyncio
async def test_major_core_and_gened_tiers(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    assert remaining[CS110].tier == TIER_MAJOR
    assert remaining[THEO101].tier == TIER_GENED
    assert remaining[HIST101].tier == TIER_GENED


@pytest.mark.asyncio
async def test_elective_minor_not_declared_alone_is_minor_tier(db_pool):
    # Studio Art declared on its own — nothing requires it, so its
    # courses should be TIER_MINOR, not promoted.
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [ART]
    )
    assert remaining[ART100].tier == TIER_MINOR
    assert remaining[ART200].tier == TIER_MINOR


@pytest.mark.asyncio
async def test_structurally_required_minor_promoted_to_major_tier(db_pool):
    # Math is required_by CS — when BOTH are declared, MATH120 (a
    # minor-only requirement, not double-counted like MATH121) should
    # be promoted to TIER_MAJOR.
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS, MATH]
    )
    assert remaining[MATH120].tier == TIER_MAJOR


@pytest.mark.asyncio
async def test_double_counted_course_takes_max_tier(db_pool):
    # MATH121 is major_core under CS AND minor under Math — even when
    # only Math is declared (not CS), if course-level logic were wrong
    # it might read gen_ed-like; confirm it's whatever satisfies the
    # highest applicable requirement when both programs are declared.
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS, MATH]
    )
    assert remaining[MATH121].tier == TIER_MAJOR  # from CS's major_core row


@pytest.mark.asyncio
async def test_categories_from_remaining_maps_tiers_to_labels(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS, MATH]
    )
    categories = categories_from_remaining(remaining)
    assert categories[CS110] == "major"
    assert categories[THEO101] == "gen_ed"
    assert categories[MATH120] == "major"  # promoted, structurally required


@pytest.mark.asyncio
async def test_unlocks_count_reflects_remaining_pool(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    # CS110 unlocks CS210 (which is also remaining) -> 1
    assert remaining[CS110].course.unlocks_count == 1
    # CS210 unlocks CS310 -> 1
    assert remaining[CS210].course.unlocks_count == 1
    # HIST101 unlocks nothing
    assert remaining[HIST101].course.unlocks_count == 0


@pytest.mark.asyncio
async def test_prereq_ids_loaded_correctly(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    assert remaining[CS210].course.prereq_ids == [CS110]
    assert remaining[CS110].course.prereq_ids == []


def test_cycle_detection_raises_on_real_cycle():
    edges = {"A": ["B"], "B": ["C"], "C": ["A"]}
    with pytest.raises(PrerequisiteCycleError):
        _check_for_cycles(edges)


def test_cycle_detection_passes_on_dag():
    edges = {"A": ["B"], "B": ["C"], "C": []}
    _check_for_cycles(edges)  # should not raise


@pytest.mark.asyncio
async def test_term_candidates_built_from_real_sections(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    candidates = await load_term_candidates(db_pool, remaining, "Fall 2026")
    course_ids = {c.course.id for c in candidates}
    # CS110 and THEO101 both have Fall 2026 sections (deliberately clashing)
    assert CS110 in course_ids
    assert THEO101 in course_ids
    # CS210 only has a Spring 2027 section
    assert CS210 not in course_ids
    for c in candidates:
        assert c.locked is False


@pytest.mark.asyncio
async def test_term_candidates_include_every_section_of_a_multi_section_course(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [ART]
    )
    candidates = await load_term_candidates(db_pool, remaining, "Fall 2026")
    art100_candidates = [c for c in candidates if c.course.id == ART100]
    # ART100 has two Fall 2026 sections (MWF 13:00 and TR 13:00) — both
    # must come back as separate candidates, not collapsed to one, so
    # the solver actually gets to choose between them (see CLAUDE.md's
    # "Multiple sections per course").
    assert len(art100_candidates) == 2
    assert {c.section.days for c in art100_candidates} == {"MWF", "TR"}


@pytest.mark.asyncio
async def test_term_candidates_exclude_list_is_respected(db_pool):
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    candidates = await load_term_candidates(
        db_pool, remaining, "Fall 2026", exclude_course_ids=frozenset({CS110})
    )
    assert CS110 not in {c.course.id for c in candidates}


@pytest.mark.asyncio
async def test_load_locked_candidates_empty_when_no_semester_plans(db_pool):
    # No semester_plans exist for this fake student — should return [],
    # not error, since this query is also read-only/FK-safe.
    remaining = await _remaining_requirements_for_declared_programs(
        db_pool, FAKE_STUDENT_ID, [CS]
    )
    locked = await load_locked_candidates(db_pool, remaining, FAKE_STUDENT_ID, "Fall 2026")
    assert locked == []
