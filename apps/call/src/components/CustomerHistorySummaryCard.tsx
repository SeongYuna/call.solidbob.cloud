import { useState, type ReactElement } from "react";
import { getCustomerHistory } from "../mock/customerHistory";
import { getSelectedMockScenarioId } from "../mock/scenarios";
import { useCallStore } from "../store/callStore";

/**
 * 재상담 고객이면 통화 시작과 함께 자동으로 뜬다 — 상담원이 고객정보·이전 문의를
 * 다시 묻지 않게. 필요서류 카드 위, 두 탭(필요서류/팝업창) 어느 쪽에서도 보인다.
 *
 * mock 전용이다 — `mock/customerHistory.ts` 주석 참고. F-3(반복 문의 연결)이
 * 서버에 생기면 시나리오 ID 대신 실제 customer_id 조회로 바꾼다.
 */
export function CustomerHistorySummaryCard(): ReactElement | null {
  const viewMode = useCallStore((state) => state.viewMode);
  const [expanded, setExpanded] = useState(true);

  if (viewMode === "history") {
    return null; // 지난 상담을 다시 보는 중이다 — "새 통화 시작" 맥락이 아니다
  }

  const history = getCustomerHistory(getSelectedMockScenarioId());
  if (history === null) {
    return null; // 처음 문의하는 고객 — 보여줄 이력이 없다
  }

  return (
    <section
      className={`customer-history-summary${expanded ? "" : " is-collapsed"}`}
      aria-label="재상담 고객 이력"
    >
      <button
        type="button"
        className="customer-history-toggle"
        aria-expanded={expanded}
        onClick={() => {
          setExpanded((value) => !value);
        }}
      >
        <span className="customer-history-badge">🔁 재상담 고객</span>
        <span className="customer-history-count">
          {`지난 상담 ${history.entries.length}건`}
        </span>
        <ChevronIcon />
      </button>
      {expanded ? (
        <div className="customer-history-body">
          <ul className="customer-history-list">
            {history.entries.map((entry) => (
              <li key={`${entry.date}-${entry.inquiryType}`}>
                <time>{entry.date}</time>
                <span>{entry.inquiryType}</span>
              </li>
            ))}
          </ul>
          <p className="customer-history-memo">
            <span className="customer-history-memo-label">메모</span>
            {history.memo}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function ChevronIcon(): ReactElement {
  return (
    <svg
      className="customer-history-chevron"
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2.4 4.4 6 8l3.6-3.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
