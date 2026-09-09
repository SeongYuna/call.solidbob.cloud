import type { ReactElement } from "react";
import type { HourlyVolume } from "../mock/standbyKpi";

interface CallVolumeChartProps {
  points: readonly HourlyVolume[];
}

const PLOT_WIDTH = 560;
const PLOT_HEIGHT = 72;
const PAD_X = 28;
const PAD_Y = 8;

export function CallVolumeChart({
  points,
}: CallVolumeChartProps): ReactElement {
  const max = Math.max(...points.map((item) => item.count), 1);
  const innerW = PLOT_WIDTH - PAD_X * 2;
  const innerH = PLOT_HEIGHT - PAD_Y * 2;
  const step = points.length > 1 ? innerW / (points.length - 1) : innerW;

  const coords = points.map((item, index) => {
    const x = PAD_X + step * index;
    const y = PAD_Y + innerH * (1 - item.count / max);
    return { x, y, ...item };
  });
  const line = coords
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
  const area = `${line} L ${coords[coords.length - 1]?.x ?? PAD_X} ${PAD_Y + innerH} L ${PAD_X} ${PAD_Y + innerH} Z`;

  return (
    <figure className="volume-chart wrapup-card">
      <figcaption className="volume-chart-title">시간대별 통화량</figcaption>
      <svg
        className="volume-chart-svg"
        viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="시간대별 통화량 mock 그래프"
      >
        <path className="volume-area" d={area} />
        <path className="volume-line" d={line} />
        {coords.map((point) => (
          <circle
            key={point.hour}
            className="volume-dot"
            cx={point.x}
            cy={point.y}
            r="3"
          />
        ))}
      </svg>
      <div className="volume-hours" aria-hidden="true">
        {points.map((item) => (
          <span key={item.hour}>{item.hour}</span>
        ))}
      </div>
    </figure>
  );
}
