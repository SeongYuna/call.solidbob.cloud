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
        <span className="supervisor-badge">
          <CheckIcon />
          관리자에게 전송됨
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

function CheckIcon(): ReactElement {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12.5 10 17.5 19 7" />
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
