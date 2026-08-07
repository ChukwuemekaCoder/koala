export type SemesterStatus = "completed" | "current" | "future";

export interface SemesterNode {
  label: string;
  status: SemesterStatus;
  flagged?: boolean;
}

interface SemesterTimelineProps {
  semesters: SemesterNode[];
}

export function SemesterTimeline({ semesters }: SemesterTimelineProps) {
  return (
    <div className="timeline">
      {semesters.map((semester) => (
        <div className="timeline-node" key={semester.label}>
          <span className={`timeline-dot timeline-dot--${semester.status}`} />
          <span
            className={`timeline-label ${semester.flagged ? "timeline-label--flagged" : ""}`}
          >
            {semester.label}
          </span>
        </div>
      ))}
    </div>
  );
}
