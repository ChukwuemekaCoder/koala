"""
Shared row-shaping helpers used across routers. Small on purpose — this
is glue between flat SQL rows and JSON response shapes, not business
logic (that lives in app.solver).
"""


def group_meetings_by_section(rows: list[dict]) -> dict[str, list[dict]]:
    """
    section_meetings is one-to-many off sections (see CLAUDE.md's "Real
    day/time overlap logic (updated — section_meetings)"), so any query
    joining it comes back one row per meeting. Groups those rows into
    {section_id: [{"days", "start_time", "end_time"}, ...]} — callers
    wrap this with whatever section/course-level fields their response
    needs, since what surrounds the meetings list differs per endpoint
    (a course dict in a semester plan vs. a bare section listing).
    """
    meetings_by_section: dict[str, list[dict]] = {}
    for r in rows:
        section_id = str(r["section_id"])
        meetings_by_section.setdefault(section_id, []).append(
            {
                "days": r["days"],
                "start_time": r["start_time"].isoformat(),
                "end_time": r["end_time"].isoformat(),
            }
        )
    return meetings_by_section
