import type {
  CallWrapUp,
  ManualSearchRequest,
  RecommendationBatch,
  RecommendationCard,
  TranscriptEvent,
} from "../types/contract";
import type { GatewayClient, GatewayListener } from "../lib/ws/types";
import { getScenario } from "./scenarios";
import { DEFAULT_LOCAL_RESOURCES } from "./localResources";
import { sentimentFromScenario } from "./sentiment";
import {
  mockAgentTts,
  mockCustomerTranslation,
} from "../lib/translation/mockSource";

/** 발화 직후 종결 상태를 보내는 간격. 실측이 아님. */
const CLOSURE_AFTER_UTTERANCE_MS = 800;
/** 발화 사이 간격을 이만큼 줄인다. 실측이 아님. */
const GAP_SHAVE_MS = 2000;
const MIN_GAP_MS = 1500;
/** 수동 검색 응답까지의 지연. 실측이 아니라 로딩 상태를 보여주기 위한 값이다. */
const MANUAL_SEARCH_MS = 800;
/** 통화 후 처리 응답까지의 지연. 역시 실측이 아니다. */
const WRAP_UP_MS = 600;

/**
 * 다산콜센터 mock 시나리오를 재생한다.
 * 발화 시각은 utterance_end_ms 를 쓰되, 발화 사이 간격만 2초 줄여 재생한다.
 */
export class MockGatewayClient implements GatewayClient {
  readonly mode = "mock" as const;
  private timers: number[] = [];
  private aborted = false;
  /** connect 시점 시나리오. 칩만 바꾸고 재생 전이면 검색·랩업이 다른 통화와 섞이지 않게 한다. */
  private playing = getScenario();

  connect(listeners: GatewayListener): void {
    this.disconnect();
    this.aborted = false;
    listeners.onStatus({ mode: "mock", connected: true });

    const scenario = getScenario();
    this.playing = scenario;
    listeners.onCallLanguage?.(scenario.targetLanguage ?? null);
    const playAt = playbackClock(scenario.transcripts);

    for (const event of scenario.transcripts) {
      this.schedule(playAt(event.utterance_end_ms), () => {
        listeners.onTranscript(event);
        const translation = mockCustomerTranslation(scenario, event.segment_id);
        if (translation !== undefined) {
          listeners.onTranslation?.(event.segment_id, translation);
        }
        const tts = mockAgentTts(scenario, event.segment_id);
        if (tts !== undefined) {
          listeners.onAgentTts?.(event.segment_id, tts);
        }
        const guard = scenario.callGuard?.[event.segment_id];
        if (guard !== undefined) {
          listeners.onCallGuard?.(event.segment_id, guard);
        }
        if (
          scenario.accentRecognition === true &&
          event.speaker === "customer"
        ) {
          listeners.onAccentRecognition?.(event.segment_id);
        }
      });
    }

    for (const batch of scenario.cardBatches) {
      const firedAt = playAt(batch.trigger_at_ms);
      // 트리거 발동 시점에 "검색 중" 신호를 먼저 보내고, internal_latency_ms 만큼
      // 뒤에 카드를 배달한다 — 실측이 아니라 로딩 인디케이터 표시용 값이다.
      this.schedule(firedAt, () => {
        listeners.onRecommendationPending?.(batch.call_id);
      });
      this.schedule(firedAt + batch.internal_latency_ms, () => {
        listeners.onRecommendation(batch);
      });
    }

    for (const item of scenario.closures) {
      const after = scenario.transcripts.find(
        (event) => event.segment_id === item.afterSegmentId,
      );
      const atMs = (after?.utterance_end_ms ?? 0) + CLOSURE_AFTER_UTTERANCE_MS;
      this.schedule(playAt(atMs), () => {
        listeners.onClosure(item.event);
      });
    }
  }

  disconnect(): void {
    this.aborted = true;
    for (const id of this.timers) {
      window.clearTimeout(id);
    }
    this.timers = [];
  }

  /**
   * 검색 엔진이 아직 없어서, 이 시나리오가 가진 카드 중 질의어와 겹치는 것을
   * 골라 돌려준다. 겹치는 것이 없으면 빈 배열이다 — 아무거나 채워 보내면
   * 화면이 근거 없는 카드를 그리게 된다(§2.3 B-6).
   */
  manualSearch(request: ManualSearchRequest): Promise<RecommendationBatch> {
    // schedule() 은 disconnect 후 콜백을 버리므로 여기서는 쓰지 않는다.
    // 버려지면 promise 가 영영 안 풀려 화면이 "검색 중" 에 갇힌다.
    return new Promise((resolve) => {
      window.setTimeout(() => {
        const pool = this.playing.cardBatches.flatMap(
          (batch) => batch.cards,
        );
        const matched = bestMatch(pool, request.query);
        resolve({
          // 수동 검색은 상담원이 직접 건 것이라 항상 "검색은 했다" — 자동 트리거 개념(fired)과는 별개다.
          fired: true,
          call_id: request.call_id,
          // 수동 검색은 트리거가 없다. 지연도 실측이 아니다.
          trigger_at_ms: 0,
          cards:
            matched === null
              ? []
              : [{ ...matched, source_type: "manual" as const }],
          internal_latency_ms: MANUAL_SEARCH_MS,
        });
      }, MANUAL_SEARCH_MS);
    });
  }

  /** 요약·분류·감정분석 모델이 없어 시나리오 문장과 C-6 건수만 돌려준다. */
  wrapUp(callId: string): Promise<CallWrapUp> {
    return new Promise((resolve) => {
      window.setTimeout(() => {
        resolve({
          call_id: callId,
          ...this.playing.wrapUp,
          local_resources:
            this.playing.wrapUp.local_resources !== undefined &&
            this.playing.wrapUp.local_resources.length > 0
              ? this.playing.wrapUp.local_resources
              : [...DEFAULT_LOCAL_RESOURCES],
          sentiment: sentimentFromScenario(this.playing, callId),
        });
      }, WRAP_UP_MS);
    });
  }

  private schedule(delayMs: number, fn: () => void): void {
    const id = window.setTimeout(() => {
      if (!this.aborted) {
        fn();
      }
    }, delayMs);
    this.timers.push(id);
  }
}

/**
 * 질의어 토큰이 카드 본문에 몇 개나 들어 있는지로 고른다. 실제 검색이 아니라
 * 데모용 근사치다 — 리랭킹·임베딩은 `ai/apps/retrieval` 의 몫이다.
 */
function bestMatch(
  pool: RecommendationCard[],
  query: string,
): RecommendationCard | null {
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((token) => token.length > 0);
  if (tokens.length === 0) {
    return null;
  }

  let best: RecommendationCard | null = null;
  let bestScore = 0;
  for (const card of pool) {
    const haystack =
      `${card.title} ${card.summary} ${card.source.doc_id} ${card.source.title}`.toLowerCase();
    const score = tokens.filter((token) => haystack.includes(token)).length;
    if (score > bestScore) {
      best = card;
      bestScore = score;
    }
  }
  return best;
}

function playbackClock(
  transcripts: TranscriptEvent[],
): (originalMs: number) => number {
  const anchors = transcripts.map((event) => event.utterance_end_ms);
  if (anchors.length === 0) {
    return (ms) => Math.max(0, ms);
  }

  const compressed = [anchors[0]];
  for (let i = 1; i < anchors.length; i += 1) {
    const gap = anchors[i] - anchors[i - 1];
    compressed.push(compressed[i - 1] + Math.max(gap - GAP_SHAVE_MS, MIN_GAP_MS));
  }

  return (originalMs: number) => {
    if (originalMs <= anchors[0]) {
      return Math.max(0, compressed[0] - (anchors[0] - originalMs));
    }
    for (let i = 1; i < anchors.length; i += 1) {
      if (originalMs <= anchors[i]) {
        const span = anchors[i] - anchors[i - 1];
        const ratio = span === 0 ? 1 : (originalMs - anchors[i - 1]) / span;
        return compressed[i - 1] + ratio * (compressed[i] - compressed[i - 1]);
      }
    }
    const last = anchors.length - 1;
    return compressed[last] + (originalMs - anchors[last]);
  };
}
