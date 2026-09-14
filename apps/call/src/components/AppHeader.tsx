import type { ReactElement } from "react";
import { isCoreApiConfigured } from "../lib/api/coreClient";
import { useCallStore } from "../store/callStore";
import { LanguageBadge } from "./LanguageBadge";
import { StandbyBackButton } from "./StandbyBackButton";

interface SessionControlsProps {
  onReplay: () => void;
  onEndCall: () => void;
  onStartNewCall?: () => void;
  onLeaveToStandby?: () => void;
}

export function BrandLockup(): ReactElement {
  return (
    <div className="brand">
      <span className="brand-logo" aria-hidden="true" />
      <span className="brand-mark">CallGuard</span>
      <span className="brand-sub">상담원 어시스트</span>
    </div>
  );
}

export function SessionControls({
  onReplay,
  onEndCall,
  onStartNewCall,
  onLeaveToStandby,
}: SessionControlsProps): ReactElement {
  const mode = useCallStore((state) => state.mode);
  const connected = useCallStore((state) => state.connected);
  const callId = useCallStore((state) => state.callId);
  const viewMode = useCallStore((state) => state.viewMode);
  const targetLanguage = useCallStore((state) => state.targetLanguage);
  const historyTargetLanguage = useCallStore(
    (state) => state.historyTargetLanguage,
  );
  const historyCallId = useCallStore((state) => state.historyCallId);
  const phase = useCallStore((state) => state.phase);
  const hasCall = useCallStore((state) => state.utterances.length > 0);
  const displayLang =
    viewMode === "history" ? historyTargetLanguage : targetLanguage;
  const displayCallId =
    viewMode === "history" ? (historyCallId ?? "대기") : (callId ?? "대기");

  const overlay =
    phase === "wrapup" || viewMode === "history";
  const liveInProgress =
    connected && phase === "live" && viewMode !== "history";

  return (
    <div className="header-meta">
      {onLeaveToStandby !== undefined ? (
        <StandbyBackButton
          liveInProgress={liveInProgress}
          onLeave={onLeaveToStandby}
        />
      ) : null}
      {phase === "live" && viewMode !== "history" ? (
        <button
          type="button"
          className="btn-outline"
          onClick={onEndCall}
          disabled={!hasCall}
          title={hasCall ? undefined : "아직 통화 내용이 없습니다"}
        >
          <svg
            className="btn-outline-icon"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="6.25" y="6.25" width="11.5" height="11.5" rx="1.5" />
          </svg>
          통화 종료
        </button>
      ) : null}
      <span className="call-id">{displayCallId}</span>
      {displayLang !== null ? <LanguageBadge lang={displayLang} /> : null}
      <span
        className={`conn-badge ${overlay ? "ended" : connected ? "on" : "off"}`}
      >
        {connected && !overlay ? (
          <span className="conn-dot" aria-hidden="true" />
        ) : null}
        {overlay ? "종료됨" : connected ? "연결됨" : "끊김"}
      </span>
      {isCoreApiConfigured() ? <span className="status">REST</span> : null}
      {mode === "mock" ? (
        <button type="button" className="btn-replay" onClick={onReplay}>
          <svg
            className="btn-replay-icon"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M6 4.75v14.5a.75.75 0 0 0 1.13.65l12.5-7.25a.75.75 0 0 0 0-1.3L7.13 4.1A.75.75 0 0 0 6 4.75z" />
          </svg>
          다시 재생
        </button>
      ) : null}
      {overlay && onStartNewCall !== undefined ? (
        <button type="button" className="btn-primary" onClick={onStartNewCall}>
          새 통화 시작
        </button>
      ) : null}
    </div>
  );
}

export function AppHeader({
  onReplay,
  onEndCall,
  onStartNewCall,
  onLeaveToStandby,
}: SessionControlsProps): ReactElement {
  const error = useCallStore((state) => state.error);
  const connected = useCallStore((state) => state.connected);
  const phase = useCallStore((state) => state.phase);
  const viewMode = useCallStore((state) => state.viewMode);
  const liveInProgress =
    connected && phase === "live" && viewMode !== "history";

  return (
    <header className="app-header">
      <div className="header-lead">
        {onLeaveToStandby !== undefined ? (
          <StandbyBackButton
            liveInProgress={liveInProgress}
            onLeave={onLeaveToStandby}
          />
        ) : null}
        <BrandLockup />
      </div>
      <SessionControls
        onReplay={onReplay}
        onEndCall={onEndCall}
        onStartNewCall={onStartNewCall}
      />
      {error !== null ? <p className="header-error">{error}</p> : null}
    </header>
  );
}
