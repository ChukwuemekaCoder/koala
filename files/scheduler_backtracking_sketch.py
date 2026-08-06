"""
Backtracking schedule solver — core algorithm sketch.

This solves ONE semester at a time: given a student's remaining degree
requirements and the sections actually offered that term, pick the best
non-conflicting set of courses within [MIN_CREDITS, MAX_CREDITS].

Design goals this sketch demonstrates:
  1. Priority ordering (tier + bottleneck score) decides WHICH courses
     to try first — this is what keeps the search fast in practice,
     since a good ordering finds a solution almost immediately and
     rarely needs to backtrack at all.
  2. Backtracking handles the cases where a greedy pick turns out to be
     wrong (a course that seemed fine blocks a higher-priority one later).
  3. Locked courses (from manual overrides) are hard constraints — they
     go in first, before the search even starts.
  4. Credit-hour bounds are enforced as pruning conditions, not
     after-the-fact validation — an invalid partial schedule is
     abandoned immediately rather than explored further.

This is intentionally simplified (no DB calls, no lookahead tiebreaking —
that's the deferred v2 feature). It's meant to be tested standalone with
mock data before wiring into FastAPI/Postgres.
"""

from dataclasses import dataclass, field
from typing import Optional

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


@dataclass
class Section:
    id: str
    course_id: str
    day_time: tuple[str, ...]  # e.g. ("MWF", "10:00-10:50")


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
    """Placeholder — real version parses day/time overlap properly."""
    return section_a.day_time == section_b.day_time


def solve_semester(
    candidates: list[Candidate],
) -> Optional[list[Candidate]]:
    """
    Entry point. Returns a valid schedule (list of chosen candidates)
    or None if no valid schedule exists within the credit bounds.
    """
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
    )
    return result


def _backtrack(
    remaining: list[Candidate],
    chosen: list[Candidate],
    total_credits: int,
) -> Optional[list[Candidate]]:
    # Base case: enough credits and nothing higher-priority left to try
    if total_credits >= MIN_CREDITS and not remaining:
        return chosen

    if not remaining:
        # Ran out of candidates without hitting the minimum — dead end.
        return None

    next_candidate, *rest = remaining

    # --- Branch 1: try INCLUDING this candidate ---
    conflict = any(
        has_time_conflict(next_candidate.section, c.section) for c in chosen
    )
    new_total = total_credits + next_candidate.course.credit_hours

    if not conflict and new_total <= MAX_CREDITS:
        result = _backtrack(
            remaining=rest,
            chosen=chosen + [next_candidate],
            total_credits=new_total,
        )
        if result is not None:
            return result
        # else: fall through and try excluding it (backtrack)

    # --- Branch 2: try EXCLUDING this candidate ---
    return _backtrack(
        remaining=rest,
        chosen=chosen,
        total_credits=total_credits,
    )


if __name__ == "__main__":
    # Minimal smoke test with mock data. CALC2 and THEO201 clash at the
    # same time slot — the solver should keep CALC2 (higher tier, and
    # scarcer: annual vs. every_semester) and route around THEO201.
    calc_2 = Course("CALC2", 4, "annual", unlocks_count=3)
    fitness = Course("FIT101", 1, "every_semester", unlocks_count=0)
    theology = Course("THEO201", 3, "every_semester", unlocks_count=1)
    data_structures = Course("CS210", 4, "every_semester", unlocks_count=4)
    econ = Course("ECON201", 3, "every_semester", unlocks_count=0)

    candidates = [
        Candidate(calc_2, Section("S1", "CALC2", ("MWF", "9:00")), tier=TIER_MAJOR),
        Candidate(fitness, Section("S2", "FIT101", ("TR", "11:00")), tier=TIER_GENED),
        Candidate(theology, Section("S3", "THEO201", ("MWF", "9:00")), tier=TIER_GENED),
        Candidate(data_structures, Section("S4", "CS210", ("TR", "9:30")), tier=TIER_MAJOR),
        Candidate(econ, Section("S5", "ECON201", ("MWF", "13:00")), tier=TIER_MINOR),
    ]

    schedule = solve_semester(candidates)
    if schedule:
        total = sum(c.course.credit_hours for c in schedule)
        print(f"Solved schedule ({total} credits):")
        for c in schedule:
            print(f"  {c.course.id} — tier {c.tier}, score {bottleneck_score(c.course):.0f}")
    else:
        print("No valid schedule found within credit bounds.")
