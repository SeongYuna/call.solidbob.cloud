import { useState, type ReactElement } from "react";
import { AdminBlacklistPanel } from "./components/AdminBlacklistPanel";
import { AgentStandbyScreen } from "./components/AgentStandbyScreen";
import { AppHeader } from "./components/AppHeader";
import { CallSummaryHost } from "./components/CallSummaryPanel";
import { ForcePasswordSetup } from "./components/ForcePasswordSetup";
import { TermsPanel } from "./components/TermsPanel";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { useGatewaySession } from "./hooks/useGatewaySession";
import { getMockAgentAccount } from "./mock/agentAuth";
import { useCallStore } from "./store/callStore";

export function App(): ReactElement {
  const { startCall, replay, leaveToStandby, manualSearch, endCall, wrapUp } =
    useGatewaySession();
  const [voluntaryPassword, setVoluntaryPassword] = useState(false);
  const phase = useCallStore((state) => state.phase);
  const shell = useCallStore((state) => state.shell);
  const viewMode = useCallStore((state) => state.viewMode);
  const summaryReturn = useCallStore((state) => state.summaryReturn);
  const resumeCall = useCallStore((state) => state.resumeCall);
  const resumeLive = useCallStore((state) => state.resumeLive);
  const enterStandby = useCallStore((state) => state.enterStandby);
  const enterAdmin = useCallStore((state) => state.enterAdmin);
  // J-3 관리자 화면은 요약보다 앞선다 — 관리자로 들어가 있는 동안 통화 요약이
  // 위에 뜨면 어느 역할인지 알 수 없다(`_project/decisions/204`).
  const showAdmin = shell === "admin";
  const showSummary = !showAdmin && (phase === "wrapup" || viewMode === "history");
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
      <div className="app-shell">
        {showAdmin ? (
          <AdminBlacklistPanel
            onExit={() => {
              enterStandby();
            }}
          />
        ) : showSummary ? (
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
          <>
            <AgentStandbyScreen
              agentName={agentName}
              onStartCall={startCall}
              onResetPassword={() => {
                setVoluntaryPassword(true);
              }}
            />
            {/* 라우터가 없는 구조라 대기화면에서 역할을 바꾼다. 데모에서 상담원과
                관리자를 오가며 보여줘야 하기 때문이다 — 실제 운영이면 계정 권한으로
                갈린다(`_project/decisions/204`). */}
            <button
              type="button"
              className="admin-entry"
              onClick={enterAdmin}
            >
              관리자 화면
            </button>
          </>
        ) : (
          <main className="panels">
            <TranscriptPanel onManualSearch={manualSearch} />
            <TermsPanel
              onReplay={replay}
              onEndCall={endCall}
              onLeaveToStandby={leaveToStandby}
            />
          </main>
        )}
      </div>
    </div>
  );
}
