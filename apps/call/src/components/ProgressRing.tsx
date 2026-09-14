import type { ReactElement } from "react";

export function ProgressRing({
  met,
  total,
}: {
  met: number;
  total: number;
}): ReactElement {
  const size = 38;
  const stroke = 2.2;
  const radius = (size - stroke) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = total === 0 ? 0 : met / total;
  const offset = circumference * (1 - ratio);

  return (
    <svg
      className={`progress-ring${met === total && total > 0 ? " is-complete" : ""}`}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true"
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="var(--line)"
        strokeWidth={stroke}
      />
      <circle
        className="progress-ring-arc"
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${center} ${center})`}
      />
      <text
        x={center}
        y={center}
        textAnchor="middle"
        dominantBaseline="central"
        className="progress-ring-label"
      >
        {`${met}/${total}`}
      </text>
    </svg>
  );
}
