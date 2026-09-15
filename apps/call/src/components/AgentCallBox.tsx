import { useEffect, type ReactElement } from "react";
import { captureAgentCallTokenFromUrl } from "../lib/agentCallToken";
import { useAgentCallSession } from "../lib/useAgentCallSession";

function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/**
 * 대기화면을 지나 통화가 시작되면 뜨는 "고객과 전화하기" 박스 — 상담원 본인의
 * 마이크로 게이트웨이에 실제로 붙는다(2026-09-14 사용자 지시). 마이크에 대고
 * 말하면 이 박스 안에 실시간으로(딜레이는 있어도 된다) 텍스트가 뜬다.
 * apps/platform 히어로의 통화 데모와 같은 배선·같은 팀 전용 토큰 규칙을 쓴다
 * — 음성 자체는 절대 녹음·전송하지 않고 브라우저 음성 인식이 만든 글자만 보낸다.
 */
export function AgentCallBox(): ReactElement {
  const { status, elapsedSeconds, turns, errorMessage, start, end } = useAgentCallSession();

  useEffect(() => {
    captureAgentCallTokenFromUrl();
  }, []);

  const active = status === "active";

  function handleToggle(): void {
    if (active || status === "connecting") {
      end("ended");
      return;
    }
    start();
  }

  return (
    <aside className="agent-call-box" role="complementary" aria-label="고객과 전화하기">
      <header className="agent-call-head">
        <p className="agent-call-title">
          <span className={`agent-call-dot${active ? " live" : ""}`} aria-hidden="true" />
          고객과 전화하기
        </p>
        <p className="agent-call-clock">{formatClock(elapsedSeconds)}</p>
      </header>

      <div className="agent-call-body">
        {status === "idle" || status === "ended" ? (
          <p className="agent-call-hint">
            통화를 시작하면 마이크로 말하는 내용이 실시간 텍스트로 여기에 표시됩니다.
          </p>
        ) : status === "no-token" ? (
          <p className="agent-call-hint">
            이 기능은 팀 내부 테스트용입니다. 지금 이 브라우저는 테스트 권한(팀 전용
            링크)이 없어 실제로 연결되지 않습니다.
          </p>
        ) : status === "unsupported" ? (
          <p className="agent-call-hint">이 브라우저는 음성 인식을 지원하지 않습니다. 크롬으로 열어주세요.</p>
        ) : status === "connecting" ? (
          <p className="agent-call-hint">연결하는 중…</p>
        ) : status === "error" ? (
          <p className="agent-call-hint">{errorMessage ?? "연결에 실패했습니다."}</p>
        ) : turns.length === 0 ? (
          <p className="agent-call-hint">마이크에 대고 말씀하시면 여기에 표시됩니다.</p>
        ) : (
          <ul className="agent-call-turns">
            {turns.map((turn) => (
              <li key={turn.id} className={turn.interim ? "interim" : undefined}>
                {turn.interim ? `… ${turn.text}` : `“${turn.text}”`}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="agent-call-note">
        브라우저 내장 음성 인식만 사용합니다 — 원본 음성은 저장·전송되지 않고, 인식된
        텍스트만 마스킹을 거쳐 처리됩니다.
      </p>

      <button type="button" className="agent-call-toggle" onClick={handleToggle}>
        {active || status === "connecting" ? "통화 종료" : "통화 시작"}
      </button>
    </aside>
  );
}
