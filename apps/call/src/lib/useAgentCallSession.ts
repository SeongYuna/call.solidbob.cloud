/**
 * 상담원 대시보드 "고객과 전화하기" 박스(AgentCallBox) — 브라우저 마이크 →
 * 게이트웨이(`/dev/text`, speaker=agent)로 이어지는 실제 배선이다.
 * apps/platform 의 `useLiveCallSession.ts`(speaker=customer)와 같은 계약을 쓴다
 * — services/gateway 의 `dev_page.ts`가 정의한 그것이다.
 *
 * ⚠ 절대 원칙: 오디오 자체를 녹음하거나 어디로도 전송하지 않는다. 브라우저
 * 내장 음성 인식(Web Speech API)이 그 자리에서 글자로 바꾼 **텍스트만**
 * WebSocket으로 보낸다 — 우리 서버·게이트웨이 어디에도 원본 음성이 닿지
 * 않는다(개인정보보호법 대응, 2026-09-14 사용자 지시).
 *
 * 팀원 전용: `?call_token=` 쿼리로 받은 값이 없으면 연결하지 않는다
 * (`lib/agentCallToken.ts`).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { readAgentCallToken } from "./agentCallToken";

export type AgentCallStatus =
  | "idle"
  | "connecting"
  | "active"
  | "ended"
  | "unsupported"
  | "no-token"
  | "error";

export interface AgentCallTurn {
  id: string;
  text: string;
  interim: boolean;
}

function gatewayDemoBase(): string {
  return (import.meta.env.VITE_GATEWAY_DEMO_BASE_URL ?? "").trim();
}

export interface AgentCallSession {
  status: AgentCallStatus;
  elapsedSeconds: number;
  turns: AgentCallTurn[];
  errorMessage: string | null;
  start: () => void;
  end: (nextStatus?: AgentCallStatus) => void;
}

export function useAgentCallSession(): AgentCallSession {
  const [status, setStatus] = useState<AgentCallStatus>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [turns, setTurns] = useState<AgentCallTurn[]>([]);
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

  const end = useCallback((nextStatus: AgentCallStatus = "ended") => {
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

    const token = readAgentCallToken();
    if (token === null) {
      setStatus("no-token");
      return;
    }

    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (Recognition === undefined) {
      setStatus("unsupported");
      return;
    }

    const base = gatewayDemoBase();
    if (base.length === 0) {
      setStatus("error");
      setErrorMessage("게이트웨이 주소가 설정되지 않았다(VITE_GATEWAY_DEMO_BASE_URL).");
      return;
    }

    setStatus("connecting");
    const callId = `test-web-agent-${Date.now()}`;
    const query = new URLSearchParams({ call_id: callId, speaker: "agent" });
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
        setErrorMessage(`게이트웨이 연결이 끊겼다 (${event.code}).`);
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
