import { useCallback, useEffect, useRef } from "react";
import { createCallMediatorClient } from "../lib/ws";
import type { CallMediatorClient } from "../lib/ws";
import type { CallWrapUp, TranscriptEvent } from "../types/contract";
import { useCallStore } from "../store/callStore";

/** 수동 검색 한 번의 결과. 못 찾은 것과 이미 있는 것을 구분한다. */
export type ManualSearchOutcome =
  | { kind: "added"; count: number }
  | { kind: "empty" }
  | { kind: "duplicate" }
  | { kind: "error"; message: string };

export interface CallMediatorSession {
  startCall: () => void;
  replay: () => void;
  leaveToStandby: () => void;
  manualSearch: (query: string) => Promise<ManualSearchOutcome>;
  endCall: () => void;
  wrapUp: () => Promise<CallWrapUp>;
}

/**
 * 같은 segment_id 의 interim 은 누적하지 않고 rAF 한 프레임에 최신 것만 반영.
 * 7.3절: requestAnimationFrame 또는 100ms 디바운스.
 */
export function useCallMediatorSession(): CallMediatorSession {
  const clientRef = useRef<CallMediatorClient | null>(null);
  const pendingRef = useRef<Map<string, TranscriptEvent>>(new Map());
  const rafRef = useRef<number>(0);

  const flushTranscripts = useCallback(() => {
    rafRef.current = 0;
    const batch = [...pendingRef.current.values()];
    pendingRef.current.clear();
    const apply = useCallStore.getState().applyTranscript;
    for (const event of batch) {
      apply(event);
    }
  }, []);

  const queueTranscript = useCallback(
    (event: TranscriptEvent) => {
      pendingRef.current.set(event.segment_id, event);
      if (rafRef.current !== 0) {
        return;
      }
      rafRef.current = window.requestAnimationFrame(flushTranscripts);
    },
    [flushTranscripts],
  );

  const attach = useCallback(
    (client: CallMediatorClient) => {
      useCallStore.getState().enterAssist();
      useCallStore.getState().resetCall();
      client.connect({
        onStarted: (callId) => {
          useCallStore.getState().applyStarted(callId);
        },
        onTranscript: queueTranscript,
        onRecommendation: (batch) => {
          useCallStore.getState().applyRecommendation(
            batch.cards,
            batch.call_id,
            batch.trigger_at_ms,
            batch.fired,
          );
        },
        onRecommendationPending: () => {
          useCallStore.getState().startCardsLoading();
        },
        onClosure: (event) => {
          useCallStore.getState().applyClosure(event);
        },
        onStatus: (status) => {
          useCallStore.getState().setStatus(status.mode, status.connected);
        },
        onError: (message) => {
          useCallStore.getState().setError(message);
        },
        onTranslation: (segmentId, event) => {
          useCallStore.getState().applyTranslation(segmentId, event);
        },
        onAgentTts: (segmentId, event) => {
          useCallStore.getState().applyAgentTts(segmentId, event);
        },
        onCallGuard: (segmentId, event) => {
          useCallStore.getState().applyCallGuard(segmentId, event);
        },
        onCompliance: (segmentId, event) => {
          useCallStore.getState().applyCompliance(segmentId, event);
        },
        onComplianceUnavailable: (segmentId, event) => {
          useCallStore.getState().applyComplianceUnavailable(segmentId, event);
        },
        onRoutingDecision: (event) => {
          useCallStore.getState().applyRoutingDecision(event);
        },
        onAccentRecognition: (segmentId) => {
          useCallStore.getState().applyAccentHint(segmentId);
        },
        onCallLanguage: (lang) => {
          useCallStore.getState().setTargetLanguage(lang);
        },
      });
    },
    [queueTranscript],
  );

  useEffect(() => {
    const client = createCallMediatorClient();
    clientRef.current = client;
    return () => {
      if (rafRef.current !== 0) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = 0;
      }
      pendingRef.current.clear();
      client.disconnect();
      clientRef.current = null;
    };
  }, []);

  const startCall = useCallback(() => {
    const client = clientRef.current;
    if (client === null) {
      return;
    }
    attach(client);
  }, [attach]);

  const replay = useCallback(() => {
    const client = clientRef.current;
    if (client === null || client.mode !== "mock") {
      return;
    }
    attach(client);
  }, [attach]);

  const manualSearch = useCallback(
    async (query: string): Promise<ManualSearchOutcome> => {
      const client = clientRef.current;
      if (client === null) {
        return { kind: "error", message: "콜 미디에이터에 연결되어 있지 않습니다." };
      }
      const callId = useCallStore.getState().callId ?? "";
      try {
        const batch = await client.manualSearch({ call_id: callId, query });
        // 못 찾은 질의가 D-4 공백 후보다. 오류는 지식베이스 문제가 아니라 세지 않는다.
        useCallStore.getState().logManualSearch(query, batch.cards.length > 0);
        if (batch.cards.length === 0) {
          return { kind: "empty" };
        }
        const added = useCallStore.getState().applyManualResult(batch.cards);
        return added === 0 ? { kind: "duplicate" } : { kind: "added", count: added };
      } catch (error) {
        return {
          kind: "error",
          message:
            error instanceof Error ? error.message : "검색에 실패했습니다.",
        };
      }
    },
    [],
  );

  // 통화를 끝내면 재생을 멈춘다. 자막이 뒤에서 계속 쌓이면 랩업이 통화 내용과 어긋난다.
  const endCall = useCallback(() => {
    clientRef.current?.disconnect();
    useCallStore.getState().endCall();
  }, []);

  const leaveToStandby = useCallback(() => {
    clientRef.current?.disconnect();
    pendingRef.current.clear();
    if (rafRef.current !== 0) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    useCallStore.getState().resumeLive();
    useCallStore.getState().enterStandby();
  }, []);

  const wrapUp = useCallback(async (): Promise<CallWrapUp> => {
    const client = clientRef.current;
    if (client === null) {
      throw new Error("콜 미디에이터에 연결되어 있지 않습니다.");
    }
    const state = useCallStore.getState();
    // `callId`는 전사·추천·판정 이벤트가 최소 한 번 와야 채워진다(§7.3 계약에
    // "통화 시작" 메시지가 따로 없다 — `w6-close-callid-missing`). 그 전에 종료를
    // 누르면 빈 문자열로 `/close`를 불러 404가 나고 요약·블랙리스트 요청까지
    // 못 쓰게 된다 — 빈 값으로는 아예 부르지 않고 원인을 알 수 있는 오류로 바꾼다.
    // 통화 시작을 직접 방송하는 메시지가 콜 미디에이터에 생기면 이 가드는 필요 없어진다.
    if (state.callId === null || state.callId.length === 0) {
      throw new Error(
        "통화 번호를 아직 받지 못했습니다 — 발화가 한 번이라도 인식된 뒤에 다시 시도해 주세요.",
      );
    }
    const segments = state.utterances.map((u) => ({
      segment_id: u.segment_id,
      speaker: u.speaker,
      text: u.text,
      is_final: u.is_final,
      utterance_end_ms: u.utterance_end_ms,
    }));
    return client.wrapUp(state.callId, segments);
  }, []);

  return { startCall, replay, leaveToStandby, manualSearch, endCall, wrapUp };
}
