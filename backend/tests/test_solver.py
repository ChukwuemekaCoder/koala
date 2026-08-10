from datetime import time

from app.solver.scheduler_backtracking_sketch import (
    TIER_GENED,
    TIER_MAJOR,
    TIER_MINOR,
    Candidate,
    Course,
    Section,
    bottleneck_score,
    has_time_conflict,
    prerequisites_satisfied,
    priority_key,
    solve_semester,
)


def section(id_="S1", course_id="C1", days="MWF", start="9:00", end="9:50"):
    h1, m1 = map(int, start.split(":"))
    h2, m2 = map(int, end.split(":"))
    return Section(id_, course_id, days, time(h1, m1), time(h2, m2))


# --- has_time_conflict ---


def test_same_day_overlapping_time_conflicts():
    a = section(days="MWF", start="9:00", end="9:50")
    b = section(days="MWF", start="9:00", end="9:50")
    assert has_time_conflict(a, b)


def test_partial_overlap_conflicts():
    a = section(days="TR", start="9:30", end="10:45")
    b = section(days="TR", start="10:00", end="11:00")
    assert has_time_conflict(a, b)


def test_disjoint_days_no_conflict_even_if_same_time():
    a = section(days="MWF", start="9:00", end="9:50")
    b = section(days="TR", start="9:00", end="9:50")
    assert not has_time_conflict(a, b)


def test_partially_shared_day_still_conflicts():
    a = section(days="MWF", start="9:00", end="9:50")
    b = section(days="MW", start="9:00", end="9:50")
    assert has_time_conflict(a, b)


def test_back_to_back_times_do_not_conflict():
    # One ends exactly when the other starts — not an overlap.
    a = section(days="MWF", start="9:00", end="9:50")
    b = section(days="MWF", start="9:50", end="10:40")
    assert not has_time_conflict(a, b)


def test_same_day_different_time_no_conflict():
    a = section(days="MWF", start="9:00", end="9:50")
    b = section(days="MWF", start="13:00", end="13:50")
    assert not has_time_conflict(a, b)


# --- prerequisites_satisfied ---


def test_no_prerequisites_always_satisfied():
    course = Course("C1", 3, "every_semester")
    assert prerequisites_satisfied(course, completed_course_ids=set())


def test_prerequisite_satisfied_when_in_completed_set():
    course = Course("C2", 3, "every_semester", prereq_ids=["C1"])
    assert prerequisites_satisfied(course, completed_course_ids={"C1"})


def test_prerequisite_not_satisfied_when_missing():
    course = Course("C2", 3, "every_semester", prereq_ids=["C1"])
    assert not prerequisites_satisfied(course, completed_course_ids=set())


def test_all_of_multiple_prerequisites_must_be_satisfied():
    course = Course("C3", 3, "every_semester", prereq_ids=["C1", "C2"])
    assert not prerequisites_satisfied(course, completed_course_ids={"C1"})
    assert prerequisites_satisfied(course, completed_course_ids={"C1", "C2"})


# --- bottleneck_score ---


def test_bottleneck_score_frequency_dominates_unlocks():
    biennial = Course("A", 3, "biennial", unlocks_count=0)
    every_sem_high_unlock = Course("B", 3, "every_semester", unlocks_count=100)
    # 100 unlocks * 5 = 500, which would beat biennial's flat 100 if it
    # didn't dominate — but the spec says frequency should win in all
    # realistic cases (unlocks_count realistically stays small).
    # This test documents the actual formula rather than assert the
    # spec's "in all realistic cases" claim for absurd unlock counts.
    assert bottleneck_score(biennial) == 100
    assert bottleneck_score(every_sem_high_unlock) == 500


def test_bottleneck_score_realistic_case_frequency_wins():
    biennial = Course("A", 3, "biennial", unlocks_count=1)
    every_semester = Course("B", 3, "every_semester", unlocks_count=4)
    assert bottleneck_score(biennial) > bottleneck_score(every_semester)


# --- priority_key ---


def test_locked_always_sorts_first():
    locked = Candidate(
        Course("A", 3, "every_semester"), section(course_id="A"), tier=TIER_GENED, locked=True
    )
    unlocked = Candidate(
        Course("B", 3, "biennial"), section(course_id="B"), tier=TIER_MAJOR, locked=False
    )
    assert priority_key(locked) < priority_key(unlocked)


def test_higher_tier_sorts_before_lower_tier_regardless_of_score():
    major = Candidate(
        Course("A", 3, "every_semester", unlocks_count=0),
        section(course_id="A"),
        tier=TIER_MAJOR,
    )
    minor_scarce = Candidate(
        Course("B", 3, "biennial", unlocks_count=10),
        section(course_id="B"),
        tier=TIER_MINOR,
    )
    assert priority_key(major) < priority_key(minor_scarce)


# --- solve_semester (integration) ---


def _candidate(
    course_id,
    credits,
    freq="every_semester",
    tier=TIER_MAJOR,
    days="MWF",
    start="9:00",
    end="9:50",
    prereq_ids=(),
    unlocks_count=0,
):
    course = Course(
        course_id,
        credits,
        freq,
        prereq_ids=list(prereq_ids),
        unlocks_count=unlocks_count,
    )
    return Candidate(
        course, section(course_id=course_id, days=days, start=start, end=end), tier=tier
    )


def test_min_credits_can_be_relaxed_for_a_final_semester():
    candidates = [_candidate("A", 3, tier=TIER_MAJOR)]
    assert solve_semester(candidates) is None  # normal 12-credit floor applies by default
    result = solve_semester(candidates, min_credits=0)
    assert result is not None
    assert sum(c.course.credit_hours for c in result) == 3


def test_solves_within_credit_bounds():
    candidates = [
        _candidate("A", 4, tier=TIER_MAJOR, start="9:00", end="9:50"),
        _candidate("B", 4, tier=TIER_MAJOR, start="10:00", end="10:50"),
        _candidate("C", 4, tier=TIER_MINOR, start="11:00", end="11:50"),
    ]
    result = solve_semester(candidates)
    assert result is not None
    total = sum(c.course.credit_hours for c in result)
    assert 12 <= total <= 18


def test_infeasible_when_cannot_reach_minimum():
    candidates = [_candidate("A", 3, tier=TIER_MAJOR)]
    assert solve_semester(candidates) is None


def test_locked_courses_always_included_even_if_low_priority():
    locked = Candidate(
        Course("LOW", 3, "every_semester"),
        section(course_id="LOW", days="MWF", start="8:00", end="8:50"),
        tier=TIER_GENED,
        locked=True,
    )
    high_priority = _candidate("HIGH", 9, freq="biennial", tier=TIER_MAJOR)
    result = solve_semester([locked, high_priority])
    assert result is not None
    ids = {c.course.id for c in result}
    assert "LOW" in ids


def test_locked_exceeding_max_credits_is_infeasible():
    locked_a = Candidate(
        Course("A", 10, "every_semester"), section(course_id="A"), tier=TIER_GENED, locked=True
    )
    locked_b = Candidate(
        Course("B", 10, "every_semester"),
        section(course_id="B", days="TR", start="9:00", end="9:50"),
        tier=TIER_GENED,
        locked=True,
    )
    assert solve_semester([locked_a, locked_b]) is None


def test_conflicting_sections_only_one_gets_scheduled():
    a = Candidate(
        Course("A", 4, "annual", unlocks_count=3),
        section(course_id="A", days="MWF", start="9:00", end="9:50"),
        tier=TIER_MAJOR,
    )
    b = Candidate(
        Course("B", 3, "every_semester", unlocks_count=1),
        section(course_id="B", days="MWF", start="9:00", end="9:50"),
        tier=TIER_GENED,
    )
    filler1 = _candidate("F1", 4, tier=TIER_MAJOR, start="10:00", end="10:50")
    filler2 = _candidate("F2", 4, tier=TIER_MINOR, start="11:00", end="11:50")
    result = solve_semester([a, b, filler1, filler2])
    assert result is not None
    ids = {c.course.id for c in result}
    assert "A" in ids  # higher tier + higher bottleneck score wins the slot
    assert "B" not in ids


def test_only_one_section_of_the_same_course_is_ever_scheduled():
    # Two sections of the same course, at different times — neither
    # conflicts with the other, so nothing time-wise stops both from
    # being included unless the solver explicitly treats them as
    # mutually exclusive alternatives for one requirement, not two
    # independent slots (see CLAUDE.md's "Multiple sections per course").
    b1 = _candidate("B", 3, tier=TIER_MAJOR, days="MWF", start="9:00", end="9:50")
    b2 = _candidate("B", 3, tier=TIER_MAJOR, days="TR", start="11:00", end="11:50")
    result = solve_semester([b1, b2], min_credits=0)
    assert result is not None
    chosen_ids = [c.course.id for c in result]
    assert chosen_ids.count("B") == 1


def test_alternate_section_scheduled_when_first_conflicts_with_higher_priority():
    a = _candidate("A", 4, tier=TIER_MAJOR, days="MWF", start="9:00", end="9:50")
    # B's first-listed section clashes with A; its second doesn't — the
    # solver should still schedule B via the alternate section rather
    # than dropping it just because its first section was unusable.
    b_conflicting = _candidate("B", 3, tier=TIER_GENED, days="MWF", start="9:00", end="9:50")
    b_alternate = _candidate("B", 3, tier=TIER_GENED, days="TR", start="11:00", end="11:50")
    result = solve_semester([a, b_conflicting, b_alternate], min_credits=0)
    assert result is not None
    ids = {c.course.id for c in result}
    assert ids == {"A", "B"}
    chosen_b = next(c for c in result if c.course.id == "B")
    assert chosen_b.section.days == "TR"  # the non-conflicting alternate, not the first section


def test_course_with_unsatisfied_prerequisite_is_excluded():
    needs_prereq = _candidate(
        "ADV", 9, freq="biennial", tier=TIER_MAJOR, prereq_ids=["INTRO"], start="8:00", end="8:50"
    )
    fillers = [
        _candidate(f"F{i}", 4, tier=TIER_MAJOR, start=f"{9 + i}:00", end=f"{9 + i}:50")
        for i in range(3)
    ]
    result = solve_semester([needs_prereq, *fillers], completed_course_ids=set())
    assert result is not None
    ids = {c.course.id for c in result}
    assert "ADV" not in ids


def test_course_with_satisfied_prerequisite_is_included():
    needs_prereq = _candidate(
        "ADV", 4, tier=TIER_MAJOR, prereq_ids=["INTRO"], start="9:00", end="9:50"
    )
    filler = _candidate("F1", 8, tier=TIER_MINOR, start="10:00", end="10:50")
    result = solve_semester([needs_prereq, filler], completed_course_ids={"INTRO"})
    assert result is not None
    ids = {c.course.id for c in result}
    assert "ADV" in ids
