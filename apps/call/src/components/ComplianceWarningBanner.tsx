import type { ReactElement } from "react";

interface ComplianceWarningBannerProps {
  detectedPhrase: string;
  suggestedPhrase: string;
  onDismiss: () => void;
}

export function ComplianceWarningBanner({
  detectedPhrase,
  suggestedPhrase,
  onDismiss,
}: ComplianceWarningBannerProps): ReactElement {
  return (
    <div
      className="compliance-banner"
      role="alert"
      aria-label={`컴플라이언스 경고: ${suggestedPhrase}`}
    >
      <span className="compliance-icon" aria-hidden="true">
        <WarnIcon />
      </span>
      <div className="compliance-copy">
        <p className="compliance-head">
          <span className="compliance-label">권장 표현</span>
          <span className="compliance-detected">{detectedPhrase}</span>
        </p>
        <p className="compliance-suggest">{suggestedPhrase}</p>
      </div>
      <button
        type="button"
        className="compliance-dismiss"
        aria-label="경고 닫기"
        onClick={onDismiss}
      >
        <DismissIcon />
      </button>
    </div>
  );
}

function WarnIcon(): ReactElement {
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
      <path d="M12 9v4M12 17h.01M10.3 4.7 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.7a2 2 0 0 0-3.4 0Z" />
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
