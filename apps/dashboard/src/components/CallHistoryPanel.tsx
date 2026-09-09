import { useMemo, type ReactElement } from "react";
import { listCallHistory } from "../lib/api/coreClient";
import { DOMAIN_COLORS } from "../lib/domainColors";
import { formatCallStartedAt } from "../lib/formatCallTime";
import { useCallStore } from "../store/callStore";
import { DEMO_DOMAIN_LABELS } from "../types/contract";

export function CallHistoryPanel(): ReactElement {
  const items = useMemo(() => listCallHistory(), []);
  const openHistory = useCallStore((state) => state.openHistory);
  const historyCallId = useCallStore((state) => state.historyCallId);

  return (
    <div className="call-history">
      <p className="call-history-heading">상담기록</p>
      <ul className="call-history-list">
        {items.map((row) => (
          <li key={row.call_id}>
            <button
              type="button"
              className={`call-history-row${historyCallId === row.call_id ? " is-active" : ""}`}
              onClick={() => {
                openHistory(row);
              }}
            >
              <time dateTime={row.started_at}>
                {formatCallStartedAt(row.started_at)}
              </time>
              <span className="call-history-badge">
                <span
                  className="arrow-select-dot"
                  style={{ background: DOMAIN_COLORS[row.domain] }}
                  aria-hidden="true"
                />
                {DEMO_DOMAIN_LABELS[row.domain]}
              </span>
              <span className="call-history-type">{row.inquiry_type}</span>
              <span className="call-history-ref">{row.customer_ref}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
