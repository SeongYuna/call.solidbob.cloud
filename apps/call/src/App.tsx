import { useEffect, useState, type ReactElement } from "react";
import { AgentCallBox } from "./components/AgentCallBox";
import { AgentStandbyScreen } from "./components/AgentStandbyScreen";
import { AppHeader } from "./components/AppHeader";
import { CallSummaryHost } from "./components/CallSummaryPanel";
import { ForcePasswordSetup } from "./components/ForcePasswordSetup";
import { GatewayOverrideBanner } from "./components/GatewayOverrideBanner";
import { TermsPanel } from "./components/TermsPanel";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { useGatewaySession } from "./hooks/useGatewaySession";
import { captureAgentTokenFromUrl } from "./lib/agentToken";
import { useAgentCallSession } from "./lib/useAgentCallSession";
import { getMockAgentAccount } from "./mock/agentAuth";
import { useCallStore } from "./store/callStore";

export function App(): ReactElement {
  const { startCall, replay, leaveToStandby, manualSearch, endCall, wrapUp } =
    useGatewaySession();
  const agentCall = useAgentCallSession();
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

  useEffect(() => {
    captureAgentTokenFromUrl();
  }, []);
  const phase = useCallStore((state) => state.phase);
  const shell = useCallStore((state) => state.shell);
  const viewMode = useCallStore((state) => state.viewMode);
  const historyView = useCallStore((state) => state.historyView);
  const summaryReturn = useCallStore((state) => state.summaryReturn);
  const resumeCall = useCallStore((state) => state.resumeCall);
  const resumeLive = useCallStore((state) => state.resumeLive);
  const enterStandby = useCallStore((state) => state.enterStandby);
  // 상담기록은 「요약 보기」・「자막 보기」 두 화면을 오갈 수 있다 — historyView가 고른다.
  const showSummary =
    phase === "wrapup" || (viewMode === "history" && historyView === "record");
  const agentName = getMockAgentAccount().name;

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

  if (voluntaryPassword) {
    return (
      <div className="app-viewport">
        <GatewayOverrideBanner />
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
      <GatewayOverrideBanner />
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
            <AgentCallBox session={agentCall} />
          </>
        )}
      </div>
    </div>
  );
}
