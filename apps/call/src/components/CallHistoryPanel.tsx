import { useEffect, useMemo, useState, type ReactElement } from "react";
import { LanguageBadge } from "./LanguageBadge";
import { listCallHistoryRows } from "../mock/callHistory";
import {
  ResolutionStats,
  SHOW_RESOLUTION_STATS,
} from "./ResolutionStats";
import { setSelectedMockScenarioId } from "../mock/scenarios";
import { formatCallStartedAt } from "../lib/formatCallTime";
import { fetchCallList, isCoreApiConfigured } from "../lib/api/coreClient";
import { useCallStore, type SummaryReturn } from "../store/callStore";
import { DEMO_DOMAIN_LABELS, type CallHistoryItem } from "../types/contract";

interface CallHistoryPanelProps {
  onReplay: () => void;
  variant?: "menu" | "page";
  returnTo?: SummaryReturn;
}

/** `w4-dashboard-live-contract` — `VITE_CORE_API_URL`이 있으면 실제 통화 목록, 없으면 mock 시나리오. */
export function CallHistoryPanel(props: CallHistoryPanelProps): ReactElement {
  return isCoreApiConfigured() ? (
    <LiveCallHistoryList variant={props.variant ?? "menu"} returnTo={props.returnTo ?? "assist"} />
  ) : (
    <MockCallHistoryList {...props} />
  );
}

function MockCallHistoryList({
  onReplay,
  variant = "menu",
  returnTo = "assist",
}: CallHistoryPanelProps): ReactElement {
  const rows = useMemo(() => listCallHistoryRows(), []);
  const openHistory = useCallStore((state) => state.openHistory);
  const historyCallId = useCallStore((state) => state.historyCallId);

  return (
    <div className={`call-history is-${variant}`}>
      <p className="call-history-heading">
        {variant === "page" ? "최근 상담기록" : "상담기록"}
      </p>
      {SHOW_RESOLUTION_STATS && variant === "menu" ? (
        <ResolutionStats />
      ) : null}
      <ul className="call-history-list">
        {rows.map((row) => (
          <li key={row.item.call_id} className="call-history-item">
            <button
              type="button"
              className={`call-history-row${historyCallId === row.item.call_id ? " is-active" : ""}`}
              onClick={() => {
                void openHistory(row.item, { returnTo });
              }}
            >
              <time dateTime={row.item.started_at}>
                {formatCallStartedAt(row.item.started_at)}
              </time>
              <span className="call-history-badge">
                {row.item.targetLanguage !== undefined ? (
                  <LanguageBadge lang={row.item.targetLanguage} compact />
                ) : (
                  <span className="call-history-flag" aria-hidden="true">
                    {row.langFlag}
                  </span>
                )}
                {DEMO_DOMAIN_LABELS[row.item.domain]}
              </span>
              <span className="call-history-type">{row.item.inquiry_type}</span>
              <span className="call-history-ref">{row.item.customer_ref}</span>
            </button>
            <button
              type="button"
              className="call-history-replay"
              title="다시 재생"
              aria-label={`${row.item.inquiry_type} 다시 재생`}
              onClick={() => {
                setSelectedMockScenarioId(row.scenarioId);
                onReplay();
              }}
            >
              <ReplayIcon />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * `GET /hub/calls` 실제 목록. mock의 "다시 재생"(시나리오 흉내)은 없다 — 실제 통화라
 * 재생할 시나리오가 없기 때문이다. 언어 배지도 목록 계약에 없어 뺐다.
 */
function LiveCallHistoryList({
  variant,
  returnTo,
}: {
  variant: "menu" | "page";
  returnTo: SummaryReturn;
}): ReactElement {
  const openHistory = useCallStore((state) => state.openHistory);
  const historyCallId = useCallStore((state) => state.historyCallId);
  const [rows, setRows] = useState<CallHistoryItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  /**
   * `customer_ref`는 발신 번호의 HMAC이다(`decisions/304`) — 화면에 원본을 그대로
   * 내지 않는다(`decisions/205` ③과 같은 원칙). 지금 받은 목록(최대 50건) 안에서
   * 같은 값이 몇 번 나오는지만 세어 "재문의 고객" 여부만 알린다 — 해시 자체는
   * 절대 렌더하지 않는다.
   */
  const repeatCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      if (row.customer_ref.length === 0) {
        continue;
      }
      counts.set(row.customer_ref, (counts.get(row.customer_ref) ?? 0) + 1);
    }
    return counts;
  }, [rows]);

  useEffect(() => {
    let alive = true;
    setStatus("loading");
    fetchCallList({ limit: 50 })
      .then((page) => {
        if (alive) {
          setRows(page.calls);
          setStatus("ready");
        }
      })
      .catch((err: unknown) => {
        if (alive) {
          setError(err instanceof Error ? err.message : "상담기록을 불러오지 못했습니다.");
          setStatus("error");
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className={`call-history is-${variant}`}>
      <p className="call-history-heading">
        {variant === "page" ? "최근 상담기록" : "상담기록"}
      </p>
      {status === "loading" ? <p className="empty">불러오는 중...</p> : null}
      {status === "error" ? <p className="empty">{error}</p> : null}
      {status === "ready" && rows.length === 0 ? (
        <p className="empty">상담기록이 없습니다.</p>
      ) : null}
      {status === "ready" && rows.length > 0 ? (
        <ul className="call-history-list">
          {rows.map((item) => (
            <li key={item.call_id} className="call-history-item">
              <button
                type="button"
                className={`call-history-row${historyCallId === item.call_id ? " is-active" : ""}`}
                onClick={() => {
                  void openHistory(item, { returnTo });
                }}
              >
                <time dateTime={item.started_at}>
                  {formatCallStartedAt(item.started_at)}
                </time>
                <span className="call-history-badge">
                  {DEMO_DOMAIN_LABELS[item.domain]}
                </span>
                <span className="call-history-type">{item.inquiry_type}</span>
                {(repeatCounts.get(item.customer_ref) ?? 0) > 1 ? (
                  <span className="call-history-ref">재문의 고객</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ReplayIcon(): ReactElement {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M6 4.75v14.5a.75.75 0 0 0 1.13.65l12.5-7.25a.75.75 0 0 0 0-1.3L7.13 4.1A.75.75 0 0 0 6 4.75z" />
    </svg>
  );
}
