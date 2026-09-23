import type { ReactElement } from "react";
import type { CustomerRiskType } from "../lib/customerRisk/detectCustomerRisk";

interface CustomerRiskBannerProps {
  type: Exclude<CustomerRiskType, "pii">;
  matchedText: string;
  guidance: string;
  supervisorNotified: boolean;
  emphasized?: boolean;
  onDismiss: () => void;
}

const COPY: Record<
  Exclude<CustomerRiskType, "pii">,
  { label: string; aria: string }
> = {
  abuse: { label: "상담원 보호 알림", aria: "abuse" },
  distress: { label: "에스컬레이션 필요 가능성", aria: "distress" },
};

export function CustomerRiskBanner({
  type,
  matchedText,
  guidance,
  supervisorNotified,
  emphasized = false,
  onDismiss,
}: CustomerRiskBannerProps): ReactElement {
  const copy = COPY[type];
  return (
    <div
      className={`compliance-banner customer-risk is-${type}${emphasized ? " is-elevated" : ""}`}
      role="alert"
      aria-label={`고객 위험 감지: ${copy.aria}`}
      data-customer-risk={type}
      data-risk-phrase={matchedText}
    >
      <span className="compliance-icon" aria-hidden="true">
        {type === "abuse" ? <ShieldIcon /> : <EscalateIcon />}
      </span>
      <div className="compliance-copy">
        <p className="compliance-head">
          <span className="compliance-label">{copy.label}</span>
          <span className="compliance-detected">{matchedText}</span>
        </p>
        <p className="compliance-suggest">{guidance}</p>
      </div>
      {supervisorNotified ? (
        // `logSupervisorAlert`는 목업이다(`lib/customerRisk/supervisorAlert.ts`) — 실제로
        // 전송되는 곳이 없다. "전송됨"이라고 쓰면 거짓이라 연동 전임을 그대로 적는다
        // (w6-qa-ui-defects-three).
        <span className="supervisor-badge" title="관리자 알림 API가 아직 없다 — 이 화면에 기록만 남는다">
          관리자 알림 연동 전
        </span>
      ) : null}
      <button
        type="button"
        className="compliance-dismiss"
        aria-label="알림 닫기"
        onClick={onDismiss}
      >
        <DismissIcon />
      </button>
    </div>
  );
}

function ShieldIcon(): ReactElement {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3 5 6v6c0 5 3.2 7.8 7 9 3.8-1.2 7-4 7-9V6l-7-3Z" />
    </svg>
  );
}

function EscalateIcon(): ReactElement {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3v12M8 11l4 4 4-4" />
      <path d="M5 19h14" />
    </svg>
  );
}

function DismissIcon(): ReactElement {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
    >
      <path d="M6 6 18 18M18 6 6 18" />
    </svg>
  );
}
