import { useEffect, useRef, useState, type ReactElement } from "react";
import { readLiveCallToken } from "../lib/liveCallToken";
import { useLiveCallSession } from "../lib/useLiveCallSession";

function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

const CALL_APP_URL = (import.meta.env.VITE_CALL_APP_URL ?? "https://call.solidbob.cloud").trim();

/**
 * 상담원 대시보드가 같은 통화에 붙을 링크 — `?call_id=`(이 통화)·`?call_token=`
 * (이미 있는 team 전용 값, `liveCallToken.ts`)을 싣는다. `call_token` 자체를 새로
 * 만들거나 다른 방식으로 노출하지 않는다 — 여전히 팀이 따로 공유하는 값이다.
 */
function buildAgentLink(callId: string, token: string): string {
  const url = new URL(CALL_APP_URL);
  url.searchParams.set("call_id", callId);
  url.searchParams.set("call_token", token);
  return url.toString();
}

/**
 * 히어로의 "통화 받기"를 누르면 뜨는 팝업 — 뒤 배경은 블러, 안에 경과 시간·
 * "상담원과 통화 중" 표시·종료 버튼을 둔다(2026-09-14 사용자 지시).
 */
export function LiveCallModal({ onClose }: { onClose: () => void }): ReactElement {
  const { status, elapsedSeconds, turns, errorMessage, callId, start, end } = useLiveCallSession();
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const copyResetRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 토큰이 없으면(일반 방문자) 링크를 만들 수 없다 — 버튼 자체를 안 보인다.
  const liveCallToken = readLiveCallToken();

  useEffect(() => {
    start();
    // 모달이 뜨는 순간 한 번만 시작한다.
  }, [start]);

  useEffect(() => {
    return () => {
      if (copyResetRef.current !== null) {
        clearTimeout(copyResetRef.current);
      }
    };
  }, []);

  function handleEndCall(): void {
    end("ended");
    onClose();
  }

  async function handleCopyAgentLink(token: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(buildAgentLink(callId, token));
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
    if (copyResetRef.current !== null) {
      clearTimeout(copyResetRef.current);
    }
    copyResetRef.current = setTimeout(() => {
      setCopyState("idle");
    }, 2000);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 backdrop-blur-md p-5"
      role="dialog"
      aria-modal="true"
      aria-label="실시간 통화 데모"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          handleEndCall();
        }
      }}
    >
      <div className="w-full max-w-[420px] rounded-[22px] border border-line bg-card p-5 text-fg shadow-[0_28px_70px_rgba(0,0,0,0.4)]">
        <header className="flex items-center justify-between gap-3">
          <p className="m-0 flex items-center gap-2 text-[13px] font-semibold">
            <span
              className={`h-2 w-2 rounded-full ${status === "active" ? "anim-rec bg-live" : "bg-muted"}`}
              aria-hidden="true"
            />
            상담원과 통화 중
          </p>
          <p className="m-0 font-mono text-[13px] text-muted">{formatClock(elapsedSeconds)}</p>
        </header>

        <div className="mt-4 min-h-[140px] max-h-[280px] overflow-y-auto rounded-xl border border-line bg-page/40 p-3">
          {status === "no-token" ? (
            <p className="m-0 text-[13px] leading-relaxed text-muted">
              이 데모는 팀 내부 테스트용입니다. 마이크로 들어오는 음성은 이 브라우저
              안에서 바로 글자로 바뀌고, 원본 음성은 어디에도 저장·전송되지
              않습니다 — 지금은 테스트 권한이 있는 팀원만 실제로 연결됩니다.
            </p>
          ) : status === "unsupported" ? (
            <p className="m-0 text-[13px] text-muted">이 브라우저는 음성 인식을 지원하지 않습니다. 크롬으로 열어주세요.</p>
          ) : status === "connecting" ? (
            <p className="m-0 text-[13px] text-muted">연결하는 중…</p>
          ) : status === "error" ? (
            <p className="m-0 text-[13px] text-muted">{errorMessage ?? "연결에 실패했습니다."}</p>
          ) : turns.length === 0 ? (
            <p className="m-0 text-[13px] text-muted">말씀하시면 실시간으로 여기에 표시됩니다.</p>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {turns.map((turn) => (
                <li
                  key={turn.id}
                  className={`text-[14px] leading-relaxed ${turn.interim ? "text-muted" : "text-fg"}`}
                >
                  {turn.interim ? `… ${turn.text}` : `“${turn.text}”`}
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="mt-3 m-0 text-[11.5px] leading-relaxed text-muted">
          브라우저 내장 음성 인식만 사용합니다 — 원본 음성은 서버로 전송·저장되지
          않고, 인식된 텍스트만 마스킹을 거쳐 처리됩니다.
        </p>

        <div className="mt-4 flex items-center justify-end gap-2">
          {liveCallToken !== null ? (
            <button
              type="button"
              onClick={() => {
                void handleCopyAgentLink(liveCallToken);
              }}
              className="rounded-full border border-line px-5 py-2.5 text-[14px] font-semibold text-fg"
            >
              {copyState === "copied"
                ? "복사됨"
                : copyState === "error"
                  ? "복사 실패"
                  : "상담원 링크 복사"}
            </button>
          ) : null}
          <button
            type="button"
            onClick={handleEndCall}
            className="rounded-full bg-amber-fill px-5 py-2.5 text-[14px] font-semibold text-[#1a1408]"
          >
            상담 종료
          </button>
        </div>
      </div>
    </div>
  );
}
