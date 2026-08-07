import type { Semester } from "../../lib/api";

interface SemesterOutlookRowProps {
  semesters: Semester[];
  currentTerm: string;
  expandedTerm: string | null;
  onSelect: (term: string) => void;
}

export function SemesterOutlookRow({
  semesters,
  currentTerm,
  expandedTerm,
  onSelect,
}: SemesterOutlookRowProps) {
  return (
    <div className="semester-outlook-row">
      {semesters.map((semester) => {
        const isCurrent = semester.term === currentTerm;
        const isExpanded = semester.term === expandedTerm;

        let statusLabel = "Planned";
        let pillClass = "pill";
        if (semester.is_flagged) {
          const count = semester.courses.length;
          statusLabel = `${count} flagged`;
          pillClass = "pill pill--attention";
        } else if (isCurrent) {
          statusLabel = "Current";
          pillClass = "pill pill--success";
        }

        return (
          <button
            type="button"
            key={semester.term}
            className={[
              "card",
              "semester-outlook-card",
              isCurrent ? "semester-outlook-card--current" : "",
              isExpanded ? "semester-outlook-card--expanded" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onSelect(semester.term)}
            aria-expanded={isExpanded}
          >
            <p className="semester-outlook-term">{semester.term}</p>
            <p className="semester-outlook-credits">{semester.total_credits} cr</p>
            <span className={pillClass}>{statusLabel}</span>
          </button>
        );
      })}
    </div>
  );
}
