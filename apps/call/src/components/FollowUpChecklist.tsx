import { useState, type ReactElement } from "react";
import { ProgressRing } from "./ProgressRing";

interface FollowUpChecklistProps {
  title: string;
  items: readonly string[];
  onComplete?: (done: ReadonlySet<number>) => void;
}

export function FollowUpChecklist({
  title,
  items,
  onComplete,
}: FollowUpChecklistProps): ReactElement {
  const [done, setDone] = useState<ReadonlySet<number>>(() => new Set());
  const met = done.size;
  const total = items.length;
  const allDone = total > 0 && met === total;

  function toggle(index: number): void {
    setDone((current) => {
      const next = new Set(current);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  function markComplete(): void {
    const next = new Set(items.map((_, index) => index));
    setDone(next);
    onComplete?.(next);
  }

  return (
    <section className="wrapup-card">
      <div className="wrapup-card-head">
        <h3>{title}</h3>
      </div>
      <div className="tally-row">
        <ProgressRing met={met} total={total} />
        <p className="evidence-tally">{`후속조치 ${total}건 중 ${met}건 완료`}</p>
      </div>
      <ul className="followup-list">
        {items.map((item, index) => (
          <li key={item}>
            <button
              type="button"
              className={`followup-item${done.has(index) ? " done" : ""}`}
              aria-pressed={done.has(index)}
              onClick={() => {
                toggle(index);
              }}
            >
              <span className="followup-box" aria-hidden="true">
                <CheckIcon />
              </span>
              <span className="followup-text">{item}</span>
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="btn-primary"
        disabled={allDone || total === 0}
        onClick={markComplete}
      >
        완료로 표시
      </button>
    </section>
  );
}

function CheckIcon(): ReactElement {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3.4 8.2 6.5 11.1 12.6 4.8" />
    </svg>
  );
}
