export function DashboardSkeleton() {
  return (
    <div className="dashboard-page">
      <div className="dashboard-inner">
        <header className="app-header">
          <div className="skeleton-block skeleton-wordmark" />
          <div className="app-header-actions">
            <div className="skeleton-block skeleton-icon-circle" />
            <div className="skeleton-block skeleton-icon-circle" />
          </div>
        </header>

        <div className="skeleton-block skeleton-greeting" />

        <div className="dashboard-timeline-wrap">
          <div className="skeleton-block skeleton-timeline" />
        </div>

        <div className="metric-cards-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <div className="card metric-card" key={i}>
              <div className="skeleton-block skeleton-line skeleton-line--label" />
              <div className="skeleton-block skeleton-line skeleton-line--value" />
            </div>
          ))}
        </div>

        <div className="skeleton-block skeleton-section-heading" />

        <div className="semester-outlook-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <div className="card semester-outlook-card" key={i}>
              <div className="skeleton-block skeleton-line skeleton-line--short" />
              <div className="skeleton-block skeleton-line skeleton-line--short" />
              <div className="skeleton-block skeleton-pill" />
            </div>
          ))}
        </div>

        <div className="card skeleton-calendar-grid" />
      </div>
    </div>
  );
}
