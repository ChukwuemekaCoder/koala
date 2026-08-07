import type { Projection } from "../../lib/api";

export function MetricCards({ projection }: { projection: Projection }) {
  const items = [
    { label: "Credits completed", value: `${projection.credits_taken}` },
    { label: "Credits in progress", value: `${projection.credits_in_progress}` },
    { label: "Credits remaining", value: `${projection.credits_remaining}` },
    { label: "Degree complete", value: `${projection.degree_percent}%` },
  ];

  return (
    <div className="metric-cards-row">
      {items.map((item) => (
        <div className="card metric-card" key={item.label}>
          <p className="metric-card-label">{item.label}</p>
          <p className="metric-card-value">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
