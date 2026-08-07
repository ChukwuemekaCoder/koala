import { SemesterTimeline, type SemesterNode } from "../SemesterTimeline";

const semesters: SemesterNode[] = [
  { label: "Fall 22", status: "completed" },
  { label: "Spring 23", status: "completed" },
  { label: "Fall 23", status: "completed" },
  { label: "Spring 24", status: "current" },
  { label: "Fall 24", status: "future" },
  { label: "Spring 25", status: "future", flagged: true },
  { label: "Fall 25", status: "future" },
  { label: "Spring 26", status: "future" },
];

interface HeroProps {
  onGetStarted: () => void;
}

export function Hero({ onGetStarted }: HeroProps) {
  return (
    <header className="section section--sage section--no-border">
      <div className="section-inner">
        <div className="hero-grid">
          <div className="card metric-card hero-flank hero-flank--left">
            <p className="metric-card-label">Credits completed</p>
            <p className="metric-card-value">94</p>
          </div>

          <div className="hero-main">
            <h1 className="two-line-heading hero-heading">
              <span className="two-line-heading-1">
                Plan every semester with confidence
              </span>
              <br />
              <span className="two-line-heading-2">
                so you graduate exactly when you planned
              </span>
            </h1>
            <p className="hero-subtext">
              koala builds your full course schedule from your majors,
              minors, and progress — then keeps it up to date every time
              something changes.
            </p>
            <button
              type="button"
              className="btn-primary hero-cta"
              onClick={onGetStarted}
            >
              Get started
            </button>
            <SemesterTimeline semesters={semesters} />
          </div>

          <div className="card metric-card hero-flank hero-flank--right">
            <p className="metric-card-label">Projected graduation</p>
            <p className="metric-card-value">May 2026</p>
          </div>
        </div>
      </div>
    </header>
  );
}
