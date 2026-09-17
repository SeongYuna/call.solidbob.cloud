/**
 * 홍보 페이지 "통화 받기" 데모 — 브라우저 마이크 → 콜 미디에이터(`/dev/text`)로
 * 이어지는 실제 배선이다. services/call-mediator의 `dev_page.ts`와 같은 계약을 쓴다.
 *
 * ⚠ 절대 원칙: 오디오 자체를 녹음하거나 어디로도 전송하지 않는다. 브라우저
 * 내장 음성 인식(Web Speech API)이 그 자리에서 글자로 바꾼 **텍스트만**
 * WebSocket으로 보낸다 — 우리 서버·콜 미디에이터 어디에도 원본 음성이 닿지
 * 않는다(개인정보보호법 대응, 2026-09-14 사용자 지시). 통화 기록 엔진은
 * `web-speech`로 남아 구글 STT(COST-1 캡)와 무관하다.
 *
 * 팀원 전용: `?call_token=` 쿼리로 받은 값이 없으면 연결하지 않는다
 * (`lib/liveCallToken.ts`) — 일반 방문자가 눌러도 데모 안내만 보인다.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { readLiveCallToken } from "./liveCallToken";

export type LiveCallStatus =
  | "idle"
  | "connecting"
  | "active"
  | "ended"
  | "unsupported"
  | "no-token"
  | "error";

export interface LiveCallTurn {
  id: string;
  text: string;
  interim: boolean;
}

function callMediatorWsBase(): string {
  return (import.meta.env.VITE_CALL_MEDIATOR_WS_URL ?? "").trim();
}

export function useLiveCallSession() {
  const [status, setStatus] = useState<LiveCallStatus>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [turns, setTurns] = useState<LiveCallTurn[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const runningRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const turnSeqRef = useRef(0);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const end = useCallback((nextStatus: LiveCallStatus = "ended") => {
    runningRef.current = false;
    stopTimer();
    const rec = recognitionRef.current;
    if (rec !== null) {
      rec.onend = null; // 정지 직후 onend가 다시 start()를 부르지 않게
      try {
        rec.stop();
      } catch {
        // 이미 멈춰 있었을 수 있다
      }
      recognitionRef.current = null;
    }
    const ws = wsRef.current;
    if (ws !== null) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "end" }));
      }
      ws.close();
      wsRef.current = null;
    }
    setStatus(nextStatus);
  }, [stopTimer]);

  const pushTurn = useCallback((text: string, interim: boolean) => {
    setTurns((prev) => {
      const withoutInterim = prev.filter((t) => !t.interim);
      if (interim) {
        if (text.trim().length === 0) {
          return withoutInterim;
        }
        return [...withoutInterim, { id: "interim", text, interim: true }];
      }
      turnSeqRef.current += 1;
      return [...withoutInterim, { id: `t-${turnSeqRef.current}`, text, interim: false }];
    });
  }, []);

  const start = useCallback(() => {
    setErrorMessage(null);
    setTurns([]);
    setElapsedSeconds(0);

    const token = readLiveCallToken();
    if (token === null) {
      setStatus("no-token");
      return;
    }

    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (Recognition === undefined) {
      setStatus("unsupported");
      return;
    }

    const base = callMediatorWsBase();
    if (base.length === 0) {
      setStatus("error");
      setErrorMessage("콜 미디에이터 주소가 설정되지 않았다(VITE_CALL_MEDIATOR_WS_URL).");
      return;
    }

    setStatus("connecting");
    const callId = `test-web-platform-${Date.now()}`;
    const query = new URLSearchParams({ call_id: callId, speaker: "customer" });
    const ws = new WebSocket(`${base}/dev/text?${query}`, ["callguard", `bearer.${token}`]);
    wsRef.current = ws;

    ws.onopen = () => {
      runningRef.current = true;
      setStatus("active");
      timerRef.current = setInterval(() => {
        setElapsedSeconds((s) => s + 1);
      }, 1000);

      const rec = new Recognition();
      recognitionRef.current = rec;
      rec.lang = "ko-KR";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          const text = result[0].transcript;
          if (result.isFinal) {
            if (text.trim().length > 0) {
              ws.send(JSON.stringify({ text, is_final: true }));
              pushTurn(text, false);
            }
          } else {
            interim += text;
          }
        }
        if (interim.trim().length > 0) {
          ws.send(JSON.stringify({ text: interim, is_final: false }));
          pushTurn(interim, true);
        }
      };
      rec.onerror = (event) => {
        if (event.error === "not-allowed") {
          setErrorMessage("마이크 권한이 거부됐다.");
          end("error");
        }
      };
      // 크롬은 조용하면 인식을 스스로 멈춘다 — 통화 중이면 다시 켠다(dev_page.ts와 동일).
      rec.onend = () => {
        if (runningRef.current) {
          try {
            rec.start();
          } catch {
            // 이미 재시작 중일 수 있다
          }
        }
      };
      rec.start();
    };

    ws.onclose = (event) => {
      if (runningRef.current) {
        setErrorMessage(`콜 미디에이터 연결이 끊겼다 (${event.code}).`);
        end("error");
      }
    };
  }, [end, pushTurn]);

  useEffect(() => {
    return () => {
      if (runningRef.current) {
        end("ended");
      }
    };
  }, [end]);

  return { status, elapsedSeconds, turns, errorMessage, start, end };
}
