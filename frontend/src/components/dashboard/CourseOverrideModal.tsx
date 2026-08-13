import { useEffect, useState } from "react";
import { IconX } from "@tabler/icons-react";
import {
  getSections,
  overrideSchedule,
  type CourseSection,
  type ScheduleCourse,
} from "../../lib/api";

const MIN_CREDITS = 12;

function formatMeetings(meetings: CourseSection["meetings"]): string {
  return meetings
    .map((m) => `${m.days} ${m.start_time.slice(0, 5)}–${m.end_time.slice(0, 5)}`)
    .join(", ");
}

interface CourseOverrideModalProps {
  accessToken: string;
  term: string;
  course: ScheduleCourse;
  semesterTotalCredits: number;
  onClose: () => void;
  onSaved: () => void;
}

export function CourseOverrideModal({
  accessToken,
  term,
  course,
  semesterTotalCredits,
  onClose,
  onSaved,
}: CourseOverrideModalProps) {
  const [sections, setSections] = useState<CourseSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [selection, setSelection] = useState<string>(course.section_id);
  const [removing, setRemoving] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSections(accessToken, course.course_id, term)
      .then((res) => setSections(res.sections))
      .catch(() => setError("Couldn't load alternative sections — try again."))
      .finally(() => setLoading(false));
  }, [accessToken, course.course_id, term]);

  const creditsIfRemoved = semesterTotalCredits - course.credit_hours;
  const blocked = removing && creditsIfRemoved < MIN_CREDITS;

  const hasChange = removing || selection !== course.section_id;
  const saveDisabled = !hasChange || blocked || saving || loading;

  function selectSection(sectionId: string) {
    setSelection(sectionId);
    setRemoving(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      if (removing) {
        await overrideSchedule(accessToken, { term, remove_course_id: course.course_id });
      } else {
        await overrideSchedule(accessToken, {
          term,
          remove_course_id: course.course_id,
          add_section_id: selection,
        });
      }
      onSaved();
    } catch {
      setError("Couldn't save that change — try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="modal-title">{course.code}</p>
            <p className="modal-subtitle">{course.title}</p>
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

        {loading ? (
          <p className="onboarding-subtext">Loading sections…</p>
        ) : (
          <div className="section-option-list">
            {sections.map((section) => {
              const checked = !removing && selection === section.section_id;
              return (
                <button
                  type="button"
                  key={section.section_id}
                  className="section-option"
                  onClick={() => selectSection(section.section_id)}
                  aria-pressed={checked}
                >
                  <span
                    className={`section-option-radio ${
                      checked ? "section-option-radio--checked" : ""
                    }`}
                  />
                  <span className="section-option-label">
                    {formatMeetings(section.meetings)}
                    {section.section_id === course.section_id && " (current)"}
                  </span>
                </button>
              );
            })}

            <hr className="modal-divider" />

            <button
              type="button"
              className={`section-option remove-option ${
                removing ? "remove-option--selected" : ""
              }`}
              onClick={() => setRemoving(true)}
              aria-pressed={removing}
            >
              <span
                className={`section-option-radio ${
                  removing ? "section-option-radio--checked" : ""
                }`}
              />
              <span className="section-option-label">Remove this course instead</span>
            </button>
          </div>
        )}

        {blocked && (
          <p className="warning-banner">
            Removing this drops you to {creditsIfRemoved} credit hours, below the{" "}
            {MIN_CREDITS}-hour minimum — add a replacement first
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
