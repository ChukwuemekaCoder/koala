import { useEffect, useMemo, useState } from "react";
import { IconX } from "@tabler/icons-react";
import { getAddableCourses, overrideSchedule, type ScheduleCourse } from "../../lib/api";
import { formatMeetings } from "../../lib/format";

const MAX_CREDITS = 18;

const CATEGORY_FILTERS: { value: "all" | ScheduleCourse["category"]; label: string }[] = [
  { value: "all", label: "All" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
  { value: "gen_ed", label: "Gen-ed" },
];

const CATEGORY_HEADINGS: Record<ScheduleCourse["category"], string> = {
  major: "Major",
  minor: "Minor",
  gen_ed: "Gen-ed",
};

interface AddCourseModalProps {
  accessToken: string;
  term: string;
  semesterTotalCredits: number;
  onClose: () => void;
  onSaved: () => void;
}

export function AddCourseModal({
  accessToken,
  term,
  semesterTotalCredits,
  onClose,
  onSaved,
}: AddCourseModalProps) {
  const [courses, setCourses] = useState<ScheduleCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] =
    useState<(typeof CATEGORY_FILTERS)[number]["value"]>("all");
  const [search, setSearch] = useState("");
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAddableCourses(accessToken, term)
      .then((res) => setCourses(res.courses))
      .catch(() => setError("Couldn't load available courses — try again."))
      .finally(() => setLoading(false));
  }, [accessToken, term]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return courses.filter((c) => {
      if (categoryFilter !== "all" && c.category !== categoryFilter) return false;
      if (!query) return true;
      return c.code.toLowerCase().includes(query) || c.title.toLowerCase().includes(query);
    });
  }, [courses, categoryFilter, search]);

  const grouped = useMemo(() => {
    const groups: Record<string, ScheduleCourse[]> = {};
    for (const course of filtered) {
      (groups[course.category] ??= []).push(course);
    }
    return groups;
  }, [filtered]);

  const selected = courses.find((c) => c.section_id === selectedSectionId) ?? null;
  const creditsIfAdded = semesterTotalCredits + (selected?.credit_hours ?? 0);
  const blocked = selected !== null && creditsIfAdded > MAX_CREDITS;
  const saveDisabled = !selected || blocked || saving || loading;

  async function handleSave() {
    if (!selectedSectionId) return;
    setSaving(true);
    setError(null);
    try {
      await overrideSchedule(accessToken, { term, add_section_id: selectedSectionId });
      onSaved();
    } catch {
      setError("Couldn't add that course — try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="modal-title">Add a course</p>
            <p className="modal-subtitle">{term}</p>
          </div>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={18} stroke={2} />
          </button>
        </div>

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

        {loading ? (
          <p className="onboarding-subtext">Loading available courses…</p>
        ) : filtered.length === 0 ? (
          <p className="onboarding-subtext">
            {courses.length === 0
              ? "Nothing left to add — every remaining course is already in your plan."
              : "No courses match that search."}
          </p>
        ) : (
          <div className="section-option-list add-course-list">
            {(["major", "minor", "gen_ed"] as const).map((category) => {
              const rows = grouped[category];
              if (!rows || rows.length === 0) return null;
              return (
                <div key={category}>
                  <p className="course-history-group-heading">
                    {CATEGORY_HEADINGS[category]}
                  </p>
                  {rows.map((course) => {
                    const checked = selectedSectionId === course.section_id;
                    return (
                      <button
                        type="button"
                        key={course.section_id}
                        className="section-option"
                        onClick={() => setSelectedSectionId(course.section_id)}
                        aria-pressed={checked}
                      >
                        <span
                          className={`section-option-radio ${
                            checked ? "section-option-radio--checked" : ""
                          }`}
                        />
                        <span className="section-option-label">
                          {course.code} — {formatMeetings(course.meetings)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}

        {blocked && (
          <p className="warning-banner">
            Adding this pushes you to {creditsIfAdded} credit hours, above the{" "}
            {MAX_CREDITS}-hour maximum — choose a lighter course or remove one first
          </p>
        )}

        {error && <p className="auth-error">{error}</p>}

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleSave}
            disabled={saveDisabled}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
