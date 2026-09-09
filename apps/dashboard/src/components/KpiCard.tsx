import type { ReactElement } from "react";

interface KpiCardProps {
  label: string;
  value: string;
  variant?: "default" | "ok" | "warn";
}

export function KpiCard({
  label,
  value,
  variant = "default",
}: KpiCardProps): ReactElement {
  return (
    <article className={`kpi-card wrapup-card is-${variant}`}>
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">
        <span className={`kpi-badge is-${variant}`}>{value}</span>
      </p>
    </article>
  );
}
