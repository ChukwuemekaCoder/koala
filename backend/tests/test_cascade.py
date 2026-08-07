from datetime import date

from app.solver.cascade import current_term_label, next_term_label


def test_current_term_label_fall_months():
    assert current_term_label(today=date(2026, 8, 6)) == "Fall 2026"
    assert current_term_label(today=date(2026, 12, 1)) == "Fall 2026"


def test_current_term_label_spring_months():
    assert current_term_label(today=date(2026, 1, 15)) == "Spring 2026"
    assert current_term_label(today=date(2026, 7, 31)) == "Spring 2026"


def test_current_term_label_honors_declared_term_over_wall_clock():
    # It's August (wall-clock -> Fall), but the student declared spring
    # as their current term (e.g. starting off-cycle) — that should win.
    assert current_term_label("spring", today=date(2026, 8, 6)) == "Spring 2026"
    assert current_term_label("fall", today=date(2026, 3, 1)) == "Fall 2026"


def test_current_term_label_falls_back_to_wall_clock_when_undeclared():
    assert current_term_label(None, today=date(2026, 8, 6)) == "Fall 2026"


def test_next_term_label_fall_to_spring_increments_year():
    assert next_term_label("Fall 2026") == "Spring 2027"


def test_next_term_label_spring_to_fall_same_year():
    assert next_term_label("Spring 2027") == "Fall 2027"
