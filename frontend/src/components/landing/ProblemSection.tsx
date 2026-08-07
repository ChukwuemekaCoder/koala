export function ProblemSection() {
  return (
    <section className="section section--white">
      <div className="section-inner problem-grid">
        <div>
          <h2 className="two-line-heading problem-heading">
            <span className="two-line-heading-1">
              Registration tools show you what's open.
            </span>
            <br />
            <span className="two-line-heading-2">
              they don't tell you what actually gets you to graduation.
            </span>
          </h2>
          <p className="problem-text">
            Picking courses semester by semester makes it easy to miss a
            prerequisite, double-book a time slot, or take a gen-ed now
            that quietly delays a degree requirement later — and by the
            time it's obvious, it's already cost you a semester.
          </p>
        </div>

        <div className="card conflict-card">
          <p className="conflict-card-label">Tuesday, 9:00–10:15am</p>
          <div className="conflict-card-blocks">
            <div className="calendar-block calendar-block--attention">
              CS 310 — Data Structures
            </div>
            <div className="calendar-block calendar-block--attention">
              THEO 201 — Christian Foundations
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
