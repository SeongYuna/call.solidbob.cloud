import { useEffect, type ReactElement } from "react";
import { captureAgentCallTokenFromUrl } from "../lib/agentCallToken";
import type { AgentCallSession } from "../lib/useAgentCallSession";

function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/**
 * 대기화면을 지나 통화가 시작되면 뜨는 "고객과 전화하기" 박스 — 상담원 본인의
 * 마이크로 콜 미디에이터에 실제로 붙는다(2026-09-14 사용자 지시). 마이크에 대고
 * 말하면 이 박스 안에 실시간으로(딜레이는 있어도 된다) 텍스트가 뜬다.
 * apps/platform 히어로의 통화 데모와 같은 배선·같은 팀 전용 토큰 규칙을 쓴다
 * — 음성 자체는 절대 녹음·전송하지 않고 브라우저 음성 인식이 만든 글자만 보낸다.
 *
 * 세션(useAgentCallSession)은 App.tsx에서 만들어 props로 받는다 — "통화받기"를
 * 누르면 연결 성공 여부(active/no-token/unsupported/error 무엇이든)와 상관없이
 * 상담기록(대시보드)이 바로 보이도록 이 박스를 숨긴다(2026-09-16 사용자 지시 —
 * 팀 전용 토큰이 없는 로컬 테스트에서도 팝업이 막고 있으면 안 된다). 마이크·WS는
 * 계속 떠 있을 수 있고 헤더의 기존 "통화 종료"가 그것까지 끊는다(`end("ended")`
 * → status "ended" → 이 박스가 다시 뜬다).
 */
export function AgentCallBox({ session }: { session: AgentCallSession }): ReactElement | null {
  const { status, elapsedSeconds, start } = session;

  useEffect(() => {
    captureAgentCallTokenFromUrl();
  }, []);

  if (status !== "idle" && status !== "ended") {
    return null;
  }

  return (
    // 2026-09-15 — 우하단 토스트에서 중앙 모달로 전환. 전화는 반드시 응답/거절해야 하는
    // 이벤트라 배경을 눌러도 닫히지 않는다(ConfirmDialog와 달리 onClick으로 닫지 않음).
    // 배경 전체를 덮는 것만으로 뒤 패널의 클릭·스크롤이 막힌다(포인터가 이 레이어에서 멎는다).
    <div className="agent-call-backdrop" role="presentation">
      <aside
        className="agent-call-box"
        role="dialog"
        aria-modal="true"
        aria-label="고객과 전화하기"
      >
        <header className="agent-call-head">
          <p className="agent-call-title">
            <span className="agent-call-dot" aria-hidden="true" />
            고객과 전화하기
          </p>
          <p className="agent-call-clock">{formatClock(elapsedSeconds)}</p>
        </header>

        <div className="agent-call-body">
          <p className="agent-call-hint">
            통화를 시작하면 마이크로 말하는 내용이 실시간 텍스트로 여기에 표시됩니다.
          </p>
        </div>

        <p className="agent-call-note">
          브라우저 내장 음성 인식만 사용합니다 — 원본 음성은 저장·전송되지 않고, 인식된
          텍스트만 마스킹을 거쳐 처리됩니다.
        </p>

        <button type="button" className="agent-call-toggle" onClick={start}>
          통화받기
        </button>
      </aside>
    </div>
  );
}
