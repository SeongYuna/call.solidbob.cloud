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
import { getMockAgentAccount } from "./mock/agentAuth";
import { useCallStore } from "./store/callStore";

export function App(): ReactElement {
  const { startCall, replay, leaveToStandby, manualSearch, endCall, wrapUp } =
    useGatewaySession();
  const [voluntaryPassword, setVoluntaryPassword] = useState(false);

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
                onEndCall={endCall}
                onLeaveToStandby={leaveToStandby}
              />
            </main>
            <AgentCallBox />
          </>
        )}
      </div>
    </div>
  );
}
