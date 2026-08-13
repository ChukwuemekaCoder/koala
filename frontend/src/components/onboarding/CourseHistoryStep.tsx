import { useEffect, useMemo, useState } from "react";
import {
  confirmProgress,
  getCourseHistory,
  type CourseHistoryEntry,
  type ProgressStatus,
} from "../../lib/api";

interface CourseHistoryStepProps {
  accessToken: string;
  onComplete: () => void;
}

const CATEGORY_FILTERS: { value: "all" | CourseHistoryEntry["category"]; label: string }[] = [
  { value: "all", label: "All" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
  { value: "gen_ed", label: "Gen-ed" },
];

const CATEGORY_HEADINGS: Record<CourseHistoryEntry["category"], string> = {
  major: "Major",
  minor: "Minor",
  gen_ed: "Gen-ed",
};

export function CourseHistoryStep({ accessToken, onComplete }: CourseHistoryStepProps) {
  const [courses, setCourses] = useState<CourseHistoryEntry[]>([]);
  const [statuses, setStatuses] = useState<Record<string, ProgressStatus>>({});
  const [categoryFilter, setCategoryFilter] =
    useState<(typeof CATEGORY_FILTERS)[number]["value"]>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCourseHistory(accessToken)
      .then((res) => {
        setCourses(res.courses);
        setStatuses(
          Object.fromEntries(res.courses.map((c) => [c.course_id, c.status])),
        );
      })
      .catch(() => setError("Couldn't load your course list — try refreshing."))
      .finally(() => setLoading(false));
  }, [accessToken]);

  function toggleStatus(courseId: string, tag: "done" | "in_progress") {
    setStatuses((prev) => ({
      ...prev,
      [courseId]: prev[courseId] === tag ? "not_taken" : tag,
    }));
  }

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return courses.filter((c) => {
      if (categoryFilter !== "all" && c.category !== categoryFilter) return false;
      if (!query) return true;
      return (
        c.code.toLowerCase().includes(query) || c.title.toLowerCase().includes(query)
      );
    });
  }, [courses, categoryFilter, search]);

  const grouped = useMemo(() => {
    const groups: Record<string, CourseHistoryEntry[]> = {};
    for (const course of filtered) {
      (groups[course.category] ??= []).push(course);
    }
    return groups;
  }, [filtered]);

  async function handleComplete() {
    setSaving(true);
    setError(null);
    try {
      const changed = courses
        .filter((c) => statuses[c.course_id] !== c.status)
        .map((c) => ({ course_id: c.course_id, status: statuses[c.course_id] }));
      if (changed.length > 0) {
        await confirmProgress(accessToken, changed);
      }
      onComplete();
    } catch {
      setError("Couldn't save your course history — try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <p className="onboarding-step-label">Step 3 of 3</p>
      <h1 className="onboarding-heading">Your course history</h1>
      <p className="onboarding-subtext">
        Tag anything you've already done or are currently taking. Everything else
        stays untaken.
      </p>

      <div className="category-filter-row">
        {CATEGORY_FILTERS.map((option) => (
          <button
            type="button"
            key={option.value}
            className={`pill pill--selectable ${
              categoryFilter === option.value ? "pill--selected" : ""
            }`}
            onClick={() => setCategoryFilter(option.value)}
            aria-pressed={categoryFilter === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="search-field course-history-search">
        <input
          type="text"
          placeholder="Search courses…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={loading}
        />
      </div>

      <div className="course-history-list">
        {(["major", "minor", "gen_ed"] as const).map((category) => {
          const rows = grouped[category];
          if (!rows || rows.length === 0) return null;
          return (
            <div key={category}>
              <p className="course-history-group-heading">{CATEGORY_HEADINGS[category]}</p>
              {rows.map((course) => {
                const status = statuses[course.course_id] ?? "not_taken";
                return (
                  <div
                    className={`course-history-row ${
                      status === "not_taken" ? "course-history-row--untaken" : ""
                    }`}
                    key={course.course_id}
                  >
                    <div className="course-history-info">
                      <span className="course-history-code">{course.code}</span>
                      <span className="course-history-title">{course.title}</span>
                    </div>
                    <span className="course-history-credits">{course.credit_hours} cr</span>
                    <div className="two-state-tag-group">
                      <button
                        type="button"
                        className={`two-state-tag ${
                          status === "done" ? "two-state-tag--done-active" : ""
                        }`}
                        onClick={() => toggleStatus(course.course_id, "done")}
                        aria-pressed={status === "done"}
                      >
                        Done
                      </button>
                      <button
                        type="button"
                        className={`two-state-tag ${
                          status === "in_progress"
                            ? "two-state-tag--in-progress-active"
                            : ""
                        }`}
                        onClick={() => toggleStatus(course.course_id, "in_progress")}
                        aria-pressed={status === "in_progress"}
                      >
                        In progress
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {error && <p className="auth-error">{error}</p>}

      <div className="onboarding-actions">
        <button
          type="button"
          className="btn-primary"
          onClick={handleComplete}
          disabled={saving || loading}
        >
          {saving ? "Generating your schedule…" : "Finish"}
        </button>
      </div>
    </div>
  );
}
