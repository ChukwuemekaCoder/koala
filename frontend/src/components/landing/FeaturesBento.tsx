import { useScrollReveal } from "../../lib/useScrollReveal";

function StatRing({ value }: { value: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value / 100);

  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke="var(--koala-border)"
        strokeWidth="8"
      />
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke="var(--koala-primary)"
        strokeWidth="8"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="56" textAnchor="middle" className="stat-ring-value">
        {value}%
      </text>
    </svg>
  );
}

export function FeaturesBento() {
  const containerRef = useScrollReveal<HTMLDivElement>();

  return (
    <section className="section section--sage">
      <div className="section-inner">
        <span className="pill section-eyebrow">Features</span>
        <div className="bento-grid" ref={containerRef}>
          <div className="card bento-card bento-wide reveal">
            <div>
              <h3>The engine plans your semesters, not just this one</h3>
              <p>
                Every recommendation weighs your declared majors and
                minors, how often each course is offered, and what it
                unlocks later — so a rare, once-a-year class never gets
                crowded out by something you could take anytime.
              </p>
            </div>
            <SemesterMiniStrip />
          </div>

          <div className="card bento-card bento-ring-card reveal">
            <StatRing value={72} />
            <h3>Track real progress</h3>
            <p>Credits taken, in progress, and remaining, always current.</p>
          </div>

          <div className="dashed-card bento-card reveal">
            <h3>Built for double majors</h3>
            <p>
              Declare as many majors and minors as you're actually
              pursuing — including ones that structurally require another,
              like a minor your major mandates.
            </p>
          </div>

          <div className="card bento-card reveal">
            <h3>Never miss a prerequisite</h3>
            <p>
              The solver won't schedule a course until everything it
              depends on is done or already in progress.
            </p>
          </div>

          <div className="card bento-card reveal">
            <h3>See the real cost of a change</h3>
            <p>
              Every edit that pushes back your graduation date shows what
              the extra semester actually costs, before you commit to it.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function SemesterMiniStrip() {
  return (
    <div className="calendar-block calendar-block--success">
      CALC 2 — locked in
    </div>
  );
}
