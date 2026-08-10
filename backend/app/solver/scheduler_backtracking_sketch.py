"""
Backtracking schedule solver — core algorithm.

This solves ONE semester at a time: given a student's remaining degree
requirements and the sections actually offered that term, pick the best
non-conflicting, prerequisite-satisfying set of courses within
[MIN_CREDITS, MAX_CREDITS].

Design goals:
  1. Priority ordering (tier + bottleneck score) decides WHICH courses
     to try first — this is what keeps the search fast in practice,
     since a good ordering finds a solution almost immediately and
     rarely needs to backtrack at all.
  2. Backtracking handles the cases where a greedy pick turns out to be
     wrong (a course that seemed fine blocks a higher-priority one later).
  3. Locked courses (from manual overrides) are hard constraints — they
     go in first, before the search even starts.
  4. Credit-hour bounds and prerequisite satisfaction are enforced as
     pruning conditions, not after-the-fact validation — an invalid
     partial schedule is abandoned immediately rather than explored
     further.

No DB calls here — see catalog.py for turning Postgres rows into the
Course/Section/Candidate objects this module operates on, and cascade.py
for the multi-semester walk that calls solve_semester() once per term.
"""

from dataclasses import dataclass, field
from datetime import time

MIN_CREDITS = 12
MAX_CREDITS = 18

# Tier weights — higher wins. Structurally-required minors get promoted
# to the same tier as majors (see required_by_program_id in the schema).
TIER_MAJOR = 3        # majors, and minors promoted via required_by
TIER_MINOR = 2        # elective, non-required minors
TIER_GENED = 1         # gen-ed / Christian coursework


@dataclass
class Course:
    id: str
    credit_hours: int
    offering_frequency: str  # "every_semester" | "annual" | "biennial"
    prereq_ids: list[str] = field(default_factory=list)
    unlocks_count: int = 0    # how many other remaining courses depend on this one
    code: str = ""            # display metadata only — not used by the solver logic
    title: str = ""


@dataclass
class Section:
    id: str
    course_id: str
    days: str        # e.g. "MWF" — any combination of M/T/W/R/F/S/U
    start_time: time
    end_time: time


@dataclass
class Candidate:
    course: Course
    section: Section
    tier: int
    locked: bool = False       # from a manual override — must be included


def bottleneck_score(course: Course) -> float:
    """
    Higher score = harder to get later, so grab it now.
    Offering frequency dominates because missing a biennial course
    costs a full year or two, which no amount of dependency weight
    can outweigh.
    """
    frequency_weight = {
        "biennial": 100,
        "annual": 50,
        "every_semester": 0,
    }.get(course.offering_frequency, 0)

    return frequency_weight + (course.unlocks_count * 5)


def priority_key(candidate: Candidate) -> tuple:
    """
    Sort key for the search order. Locked courses always come first
    (they're not really a "choice" anymore). Otherwise: tier first,
    then bottleneck score within the tier.
    """
    return (
        0 if candidate.locked else 1,
        -candidate.tier,
        -bottleneck_score(candidate.course),
    )


def has_time_conflict(section_a: Section, section_b: Section) -> bool:
    """
    Two sections conflict only if their day-letters share a character
    AND their time ranges overlap.
    """
    shares_day = any(d in section_b.days for d in section_a.days)
    overlaps_time = (
        section_a.start_time < section_b.end_time
        and section_b.start_time < section_a.end_time
    )
    return shares_day and overlaps_time


def prerequisites_satisfied(
    course: Course, completed_course_ids: set[str]
) -> bool:
    """
    A course's prerequisites are satisfied if every prerequisite is in
    `completed_course_ids` — the union of what's `done`/`in_progress`
    in student_progress plus whatever the solver already chose in
    strictly earlier semesters of the current multi-semester run (see
    cascade.py). Courses with no prerequisites are trivially satisfied.
    """
    return all(prereq_id in completed_course_ids for prereq_id in course.prereq_ids)


def solve_semester(
    candidates: list[Candidate],
    completed_course_ids: set[str] | None = None,
    min_credits: int = MIN_CREDITS,
) -> list[Candidate] | None:
    """
    Entry point. Returns a valid schedule (list of chosen candidates)
    or None if no valid schedule exists within the credit bounds and
    prerequisite constraints.

    `min_credits` defaults to the standard MIN_CREDITS floor, but callers
    solving a student's final semester (fewer remaining requirements
    than a full course load) should pass a lower value — otherwise a
    legitimately-finished plan would be reported as infeasible purely
    for having nothing left to fill the last semester to 12 credits.
    This doesn't change the two gaps this module was built to fill
    (conflict/prerequisite pruning); it's an additive parameter for a
    real edge case the walk-forward cascade (cascade.py) hits.
    """
    completed_course_ids = completed_course_ids or set()

    ordered = sorted(candidates, key=priority_key)
    locked = [c for c in ordered if c.locked]
    choosable = [c for c in ordered if not c.locked]

    locked_credits = sum(c.course.credit_hours for c in locked)
    if locked_credits > MAX_CREDITS:
        # Locked courses alone already exceed the cap — infeasible,
        # caller should surface this to the student rather than search.
        return None

    result = _backtrack(
        remaining=choosable,
        chosen=list(locked),
        total_credits=locked_credits,
        completed_course_ids=completed_course_ids,
        min_credits=min_credits,
    )
    return result


def _backtrack(
    remaining: list[Candidate],
    chosen: list[Candidate],
    total_credits: int,
    completed_course_ids: set[str],
    min_credits: int,
) -> list[Candidate] | None:
    # Base case: enough credits and nothing higher-priority left to try
    if total_credits >= min_credits and not remaining:
        return chosen

    if not remaining:
        # Ran out of candidates without hitting the minimum — dead end.
        return None

    next_candidate, *rest = remaining

    # --- Branch 1: try INCLUDING this candidate ---
    # A course can have multiple sections as candidates (mutually
    # exclusive alternatives, not independent requirement slots — see
    # CLAUDE.md's "Multiple sections per course"). If this course is
    # already satisfied by a section chosen earlier in the search,
    # this candidate is never includable, same as a time conflict —
    # falling through to the exclude-branch below naturally advances
    # to the next candidate, which is how an alternate section of a
    # DIFFERENT course still gets a fair try.
    already_scheduled = any(
        c.course.id == next_candidate.course.id for c in chosen
    )
    conflict = already_scheduled or any(
        has_time_conflict(next_candidate.section, c.section) for c in chosen
    )
    prereqs_ok = prerequisites_satisfied(next_candidate.course, completed_course_ids)
    new_total = total_credits + next_candidate.course.credit_hours

    if not conflict and prereqs_ok and new_total <= MAX_CREDITS:
        result = _backtrack(
            remaining=rest,
            chosen=chosen + [next_candidate],
            total_credits=new_total,
            completed_course_ids=completed_course_ids,
            min_credits=min_credits,
        )
        if result is not None:
            return result
        # else: fall through and try excluding it (backtrack)

    # --- Branch 2: try EXCLUDING this candidate ---
    return _backtrack(
        remaining=rest,
        chosen=chosen,
        total_credits=total_credits,
        completed_course_ids=completed_course_ids,
        min_credits=min_credits,
    )


if __name__ == "__main__":
    # Minimal smoke test with mock data. CALC2 and THEO201 clash at the
    # same time slot — the solver should keep CALC2 (higher tier, and
    # scarcer: annual vs. every_semester) and route around THEO201.
    # CS210 requires CALC1, which IS satisfied here (see
    # completed_course_ids below) — see test_solver.py for the
    # unsatisfied-prerequisite case, which prunes a course out entirely
    # regardless of how well it otherwise scores.
    calc_2 = Course("CALC2", 4, "annual", unlocks_count=3)
    fitness = Course("FIT101", 1, "every_semester", unlocks_count=0)
    theology = Course("THEO201", 3, "every_semester", unlocks_count=1)
    data_structures = Course(
        "CS210", 4, "every_semester", prereq_ids=["CALC1"], unlocks_count=4
    )
    econ = Course("ECON201", 3, "every_semester", unlocks_count=0)

    candidates = [
        Candidate(calc_2, Section("S1", "CALC2", "MWF", time(9, 0), time(9, 50)), tier=TIER_MAJOR),
        Candidate(fitness, Section("S2", "FIT101", "TR", time(11, 0), time(11, 50)), tier=TIER_GENED),
        Candidate(theology, Section("S3", "THEO201", "MWF", time(9, 0), time(9, 50)), tier=TIER_GENED),
        Candidate(data_structures, Section("S4", "CS210", "TR", time(9, 30), time(10, 45)), tier=TIER_MAJOR),
        Candidate(econ, Section("S5", "ECON201", "MWF", time(13, 0), time(13, 50)), tier=TIER_MINOR),
    ]

    schedule = solve_semester(candidates, completed_course_ids={"CALC1"})
    if schedule:
        total = sum(c.course.credit_hours for c in schedule)
        print(f"Solved schedule ({total} credits):")
        for c in schedule:
            print(f"  {c.course.id} — tier {c.tier}, score {bottleneck_score(c.course):.0f}")
    else:
        print("No valid schedule found within credit bounds.")
