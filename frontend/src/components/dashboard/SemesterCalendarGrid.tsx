import { IconLock } from "@tabler/icons-react";
import type { Semester, ScheduleCourse } from "../../lib/api";

const DAYS = ["M", "T", "W", "R", "F"] as const;
const DAY_LABELS: Record<string, string> = {
  M: "Mon",
  T: "Tue",
  W: "Wed",
  R: "Thu",
  F: "Fri",
};

// Covers the seed catalog's 9:00-14:15 range with room on both sides —
// wide enough for any realistic weekday course time.
const GRID_START_MIN = 8 * 60;
const GRID_END_MIN = 18 * 60;
const GRID_RANGE_MIN = GRID_END_MIN - GRID_START_MIN;

function timeToMinutes(isoTime: string): number {
  const [h, m] = isoTime.split(":").map(Number);
  return h * 60 + m;
}

function blockColorClass(course: ScheduleCourse): string {
  if (course.is_flagged || course.is_locked) return "calendar-block--attention";
  if (course.category === "major") return "calendar-block--success";
  return "calendar-block--other";
}

export function SemesterCalendarGrid({ semester }: { semester: Semester }) {
  if (semester.courses.length === 0) {
    return (
      <div className="calendar-grid-wrap">
        <p className="calendar-grid-empty">No courses planned for this semester yet.</p>
      </div>
    );
  }

  return (
    <div className="calendar-grid-wrap">
      {semester.is_flagged && semester.flag_reason && (
        <p className="calendar-grid-caption">{semester.flag_reason}</p>
      )}

      <div className="calendar-grid">
        <div className="calendar-grid-days">
          {DAYS.map((day) => (
            <div className="calendar-grid-day-label" key={day}>
              {DAY_LABELS[day]}
            </div>
          ))}
        </div>

        <div className="calendar-grid-body">
          {DAYS.map((day) => (
            <div className="calendar-grid-day-col" key={day}>
              {semester.courses
                .filter((course) => course.days.includes(day))
                .map((course) => {
                  const startMin = timeToMinutes(course.start_time);
                  const endMin = timeToMinutes(course.end_time);
                  const top = ((startMin - GRID_START_MIN) / GRID_RANGE_MIN) * 100;
                  const height = ((endMin - startMin) / GRID_RANGE_MIN) * 100;
                  return (
                    <div
                      key={`${course.course_id}-${day}`}
                      className={`calendar-block ${blockColorClass(course)}`}
                      style={{
                        top: `${top}%`,
                        height: `${Math.max(height, 4)}%`,
                      }}
                      title={`${course.title} — ${course.start_time.slice(0, 5)}–${course.end_time.slice(0, 5)}`}
                    >
                      {course.is_locked && <IconLock size={12} stroke={2} />}
                      <span>{course.code}</span>
                    </div>
                  );
                })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
