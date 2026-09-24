import { useState, type ReactElement } from "react";
import { AgentCallBox } from "./components/AgentCallBox";
import { AgentLoginScreen } from "./components/AgentLoginScreen";
import { AgentStandbyScreen } from "./components/AgentStandbyScreen";
import { AppHeader } from "./components/AppHeader";
import { CallSummaryHost } from "./components/CallSummaryPanel";
import { ForcePasswordSetup } from "./components/ForcePasswordSetup";
import { CallMediatorOverrideBanner } from "./components/CallMediatorOverrideBanner";
import { TermsPanel } from "./components/TermsPanel";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { useAgentAuth } from "./hooks/useAgentAuth";
import { useCallMediatorSession } from "./hooks/useCallMediatorSession";
import { useAgentCallSession } from "./lib/useAgentCallSession";
import { getMockAgentAccount } from "./mock/agentAuth";
import { useCallStore } from "./store/callStore";

export function App(): ReactElement {
  const { startCall, replay, leaveToStandby, manualSearch, endCall, wrapUp } =
    useCallMediatorSession();
  const agentCall = useAgentCallSession();
  const agentAuth = useAgentAuth();
  const [voluntaryPassword, setVoluntaryPassword] = useState(false);

  // "통화받기"를 누르면 AgentCallBox가 사라지고 대시보드(상담기록)가 보인다 —
  // 그래도 마이크·WS는 계속 떠 있으므로, 헤더의 기존 "통화 종료"가 이것도 함께 끊는다
  // (2026-09-16 사용자 지시: 별도 상태표시는 두지 않고 기존 종료 버튼에 합친다).
  function endCallAndAgentSession(): void {
    if (agentCall.status === "active" || agentCall.status === "connecting") {
      agentCall.end("ended");
    }
    endCall();
  }

  const phase = useCallStore((state) => state.phase);
  const shell = useCallStore((state) => state.shell);
  const mode = useCallStore((state) => state.mode);
  const viewMode = useCallStore((state) => state.viewMode);
  const historyView = useCallStore((state) => state.historyView);
  const summaryReturn = useCallStore((state) => state.summaryReturn);
  const resumeCall = useCallStore((state) => state.resumeCall);
  const resumeLive = useCallStore((state) => state.resumeLive);
  const enterStandby = useCallStore((state) => state.enterStandby);
  // 상담기록은 「요약 보기」・「자막 보기」 두 화면을 오갈 수 있다 — historyView가 고른다.
  const showSummary =
    phase === "wrapup" || (viewMode === "history" && historyView === "record");
  const agentName = agentAuth.displayName ?? getMockAgentAccount().name;

  function closeSummary(): void {
    if (viewMode === "history") {
      resumeLive();
      if (summaryReturn === "standby") {
        enterStandby();
      }
      return;
    }
    resumeCall();
  }

  if (agentAuth.status === "checking") {
    return (
      <div className="app-viewport">
        <div className="app-shell" />
      </div>
    );
  }

  if (agentAuth.status === "unauthenticated") {
    return (
      <div className="app-viewport">
        <div className="app-shell">
          <AgentLoginScreen error={agentAuth.error} onLogin={agentAuth.login} />
        </div>
      </div>
    );
  }

  if (voluntaryPassword) {
    return (
      <div className="app-viewport">
        <CallMediatorOverrideBanner />
        <div className="app-shell">
          <ForcePasswordSetup
            mode="voluntary"
            onComplete={() => {
              setVoluntaryPassword(false);
            }}
            onCancel={() => {
              setVoluntaryPassword(false);
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="app-viewport">
      <CallMediatorOverrideBanner />
      <div className="app-shell">
        {showSummary ? (
          <>
            <AppHeader
              onReplay={replay}
              onEndCall={endCall}
              onStartNewCall={replay}
              onLeaveToStandby={leaveToStandby}
            />
            <CallSummaryHost
              onClose={closeSummary}
              onStartNewCall={replay}
              onWrapUp={wrapUp}
            />
          </>
        ) : shell === "standby" ? (
          <AgentStandbyScreen
            agentName={agentName}
            onStartCall={startCall}
            onResetPassword={() => {
              setVoluntaryPassword(true);
            }}
            onLogout={agentAuth.logout}
          />
        ) : (
          <>
            <main className="panels">
              <TranscriptPanel onManualSearch={manualSearch} />
              <TermsPanel
                onReplay={replay}
                onEndCall={endCallAndAgentSession}
                onLeaveToStandby={leaveToStandby}
              />
            </main>
            {/* 합성 통화 재생(mock 시나리오)에는 받을 실제 전화가 없다 — 재생 중엔
                이 "통화받기" 모달이 자막을 덮지 않게 아예 안 띄운다. 실제 라이브
                통화(mode==="live")에서의 동작은 그대로 유지한다(2026-09-22). */}
            {mode === "live" ? <AgentCallBox session={agentCall} /> : null}
            {/* 토큰 없음·마이크 거부·인식 미지원·WS 거절(1006/1008) 안내(w6-qa-call-screen-fixes
                Q-48) — AgentCallBox는 실패해도 조용히 사라지므로(2026-09-16 결정, 로컬 테스트를
                막지 않으려고), 안내는 그 박스가 아니라 여기 따로 남긴다. */}
            {mode === "live" && agentCall.errorMessage !== null ? (
              <p className="header-error agent-call-error" role="alert">
                {agentCall.errorMessage}
                <button
                  type="button"
                  className="agent-call-dismiss"
                  aria-label="안내 닫기"
                  onClick={agentCall.dismissError}
                >
                  ✕
                </button>
              </p>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
