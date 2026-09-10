import { create } from "zustand";
import { cardSourceType, hasCardSource } from "../types/contract";
import type {
  CallHistoryItem,
  ClosureEvent,
  MaskType,
  RecommendationCard,
  Speaker,
  TranscriptEvent,
  TranscriptQuerySegment,
  MaskedSpan,
  TranslatedUtterance,
  AgentTtsStatus,
  CallGuardFlag,
} from "../types/contract";
import { getHistoryPlayback } from "../lib/api/coreClient";
import { getScenarioById } from "../mock/scenarios";
import type { GatewayMode } from "../lib/ws";
import { sliceByCodepoints } from "../lib/text/codepoints";
import type { TargetLanguage } from "../lib/language/languageMeta";
import {
  reportBlackConsumer,
  type BlackConsumerFlag,
} from "../lib/customerRisk/blackConsumerFlag";

export interface Utterance {
  segment_id: string;
  speaker: Speaker;
  text: string;
  plain_text?: string;
  masked: MaskedSpan[];
  is_final: boolean;
  utterance_end_ms: number;
}

export interface MaskingLogEntry {
  id: string;
  segment_id: string;
  type: MaskType;
  span: [number, number];
  excerpt: string;
  utterance_end_ms: number;
}

export interface PanelCard {
  card: RecommendationCard;
  trigger_at_ms: number;
  closure: ClosureEvent | null;
  settled: boolean;
}

/** 통화 중인가, 통화 후 처리 중인가. */
export type CallPhase = "live" | "wrapup";

/** 왼쪽 자막이 실시간인지, 상담기록인지. 실시간 발화 배열은 건드리지 않는다. */
export type TranscriptViewMode = "live" | "history";

/** 로그인 직후 대기인지, 통화 어시스트인지. */
export type AgentShell = "standby" | "assist";

/** 통화 후 요약에서 돌아갈 자리. */
export type SummaryReturn = "standby" | "assist";

/**
 * 상담원이 직접 찾은 기록. 못 찾은 질의가 §2.5 D-4 지식베이스 공백 후보다 —
 * 자동 추천이 놓친 것은 화면 밖에서 알 수 없으므로, 여기서 관찰되는 것만 센다.
 */
export interface ManualSearchLogEntry {
  query: string;
  found: boolean;
}

/**
 * 상담원이 이 카드를 실제로 썼는지. **지식베이스 보강용 피드백이지 상담원 평가가 아니다** —
 * 화면 어디에도 이 값으로 좋고 나쁨을 판정하는 문구를 두지 않는다.
 */
export interface CardAdoption {
  call_id: string;
  card_id: string;
  adopted: boolean;
}

export interface CallState {
  mode: GatewayMode;
  connected: boolean;
  error: string | null;
  phase: CallPhase;
  shell: AgentShell;
  summaryReturn: SummaryReturn;
  callId: string | null;
  /** A-5. 실시간 통화의 대상 언어. 한국어 전용 mock은 null. */
  targetLanguage: TargetLanguage | null;
  utterances: Utterance[];
  viewMode: TranscriptViewMode;
  historyCallId: string | null;
  historyStartedAt: string | null;
  historySegments: TranscriptQuerySegment[];
  historyTargetLanguage: TargetLanguage | null;
  /** 히스토리 모드 전용. 실시간 translations 과 섞지 않는다. */
  historyTranslations: Record<string, TranslatedUtterance>;
  historyAgentTts: Record<string, AgentTtsStatus>;
  historyCallGuard: Record<string, CallGuardFlag>;
  historyAccentHints: Record<string, true>;
  /** 히스토리 모드 전용. 실시간 cards 와 섞지 않는다. */
  historyCards: PanelCard[];
  cards: PanelCard[];
  /** 가장 최근 추천 응답의 fired 값. 응답을 아직 못 받았으면 null. */
  lastFired: boolean | null;
  /** 카드 추천 요청을 보낸 뒤 응답(cards 또는 fired:false)을 기다리는 중인가. */
  cardsLoading: boolean;
  maskingLog: MaskingLogEntry[];
  manualSearches: ManualSearchLogEntry[];
  /** 카드 식별자 → 채택 기록. 통화가 바뀌면 함께 비워진다. */
  adoptions: Record<string, CardAdoption>;
  closure: ClosureEvent | null;
  /** A-5 mock. 키는 TranscriptEvent.segment_id. */
  translations: Record<string, TranslatedUtterance>;
  agentTts: Record<string, AgentTtsStatus>;
  /** C-6 mock. 키는 TranscriptEvent.segment_id. */
  callGuard: Record<string, CallGuardFlag>;
  /** A-5 ⓑ. 키만. 점수는 없다. */
  accentHints: Record<string, true>;
  /** C-6 확장. 상담원이 통화 종료 시 수동으로 분류한 결과 — 자동 탐지가 아니다. */
  blackConsumerFlag: BlackConsumerFlag | null;
  applyTranscript: (event: TranscriptEvent) => void;
  applyRecommendation: (
    cards: RecommendationCard[],
    callId: string,
    triggerAtMs: number,
    fired: boolean,
  ) => void;
  /** 카드 추천 요청이 나가 응답을 기다리는 중임을 표시한다. */
  startCardsLoading: () => void;
  /** 수동 검색 결과를 패널에 붙이고, 실제로 새로 추가된 건수를 돌려준다. */
  applyManualResult: (cards: RecommendationCard[]) => number;
  logManualSearch: (query: string, found: boolean) => void;
  toggleAdoption: (card: RecommendationCard) => void;
  endCall: () => void;
  resumeCall: () => void;
  applyClosure: (event: ClosureEvent) => void;
  settleClosure: (closureType: ClosureEvent["closure_type"]) => void;
  setStatus: (mode: GatewayMode, connected: boolean) => void;
  setError: (message: string) => void;
  applyTranslation: (
    transcriptSegmentId: string,
    event: TranslatedUtterance,
  ) => void;
  applyAgentTts: (transcriptSegmentId: string, event: AgentTtsStatus) => void;
  applyCallGuard: (transcriptSegmentId: string, event: CallGuardFlag) => void;
  applyAccentHint: (transcriptSegmentId: string) => void;
  flagBlackConsumer: (callId: string) => void;
  setTargetLanguage: (lang: TargetLanguage | null) => void;
  resetCall: () => void;
  enterAssist: () => void;
  enterStandby: () => void;
  openHistory: (
    item: CallHistoryItem,
    options?: { returnTo?: SummaryReturn },
  ) => void;
  resumeLive: () => void;
}

const emptyCall = {
  phase: "live" as CallPhase,
  callId: null as string | null,
  targetLanguage: null as TargetLanguage | null,
  utterances: [] as Utterance[],
  viewMode: "live" as TranscriptViewMode,
  historyCallId: null as string | null,
  historyStartedAt: null as string | null,
  historySegments: [] as TranscriptQuerySegment[],
  historyTargetLanguage: null as TargetLanguage | null,
  historyTranslations: {} as Record<string, TranslatedUtterance>,
  historyAgentTts: {} as Record<string, AgentTtsStatus>,
  historyCallGuard: {} as Record<string, CallGuardFlag>,
  historyAccentHints: {} as Record<string, true>,
  historyCards: [] as PanelCard[],
  cards: [] as PanelCard[],
  lastFired: null as boolean | null,
  cardsLoading: false,
  maskingLog: [] as MaskingLogEntry[],
  manualSearches: [] as ManualSearchLogEntry[],
  adoptions: {} as Record<string, CardAdoption>,
  closure: null as ClosureEvent | null,
  translations: {} as Record<string, TranslatedUtterance>,
  agentTts: {} as Record<string, AgentTtsStatus>,
  callGuard: {} as Record<string, CallGuardFlag>,
  accentHints: {} as Record<string, true>,
  blackConsumerFlag: null as BlackConsumerFlag | null,
};

/**
 * 카드 식별자이자 중복 판정 키 — 문서 기준이다. 같은 조항이 자동·수동으로 두 번 뜨면
 * 상담원이 서로 다른 근거로 읽는다. 채택 기록도 같은 기준을 써야 자동 추천으로
 * 승격돼도 기록이 끊기지 않는다.
 */
export function cardId(card: RecommendationCard): string {
  return `${card.source.doc_id}\0${card.title}`;
}

function isAuto(item: PanelCard): boolean {
  return cardSourceType(item.card) === "auto";
}

/**
 * F-2(필요서류) 게이트는 자동 추천 카드에만 붙인다. 상담원이 직접 찾아온 카드에
 * 붙으면 서류 목록이 그 검색 결과에 딸린 것처럼 읽힌다.
 */
function attachIndex(cards: PanelCard[], event: ClosureEvent): number {
  const sameType = cards.findIndex(
    (item) => item.closure?.closure_type === event.closure_type,
  );
  if (sameType !== -1) {
    return sameType;
  }
  for (let i = cards.length - 1; i >= 0; i -= 1) {
    if (cards[i].closure === null && isAuto(cards[i])) {
      return i;
    }
  }
  for (let i = cards.length - 1; i >= 0; i -= 1) {
    if (isAuto(cards[i])) {
      return i;
    }
  }
  return -1;
}

function withClosure(
  cards: PanelCard[],
  event: ClosureEvent,
): PanelCard[] {
  if (cards.length === 0) {
    return cards;
  }
  const index = attachIndex(cards, event);
  if (index === -1) {
    return cards;
  }
  return cards.map((item, i) =>
    i === index ? { ...item, closure: event, settled: false } : item,
  );
}

/** 끝난 통화: 시나리오가 가진 카드를 한꺼번에. 실시간처럼 순차로 쌓지 않는다. */
function panelFromScenario(scenario: {
  cardBatches: { trigger_at_ms: number; cards: RecommendationCard[] }[];
  closures: { event: ClosureEvent }[];
}): PanelCard[] {
  const cards: PanelCard[] = [];
  const seen = new Set<string>();
  for (const batch of scenario.cardBatches) {
    for (const card of batch.cards) {
      if (!hasCardSource(card)) {
        continue;
      }
      const id = cardId(card);
      if (seen.has(id)) {
        continue;
      }
      seen.add(id);
      cards.push({
        card,
        trigger_at_ms: batch.trigger_at_ms,
        closure: null,
        settled: false,
      });
    }
  }
  return scenario.closures.reduce(
    (acc, item) => withClosure(acc, item.event),
    cards,
  );
}

export function evidenceTally(closure: ClosureEvent): {
  met: number;
  total: number;
} {
  const keys = Object.keys(closure.evidence);
  return {
    total: keys.length,
    met: keys.filter((key) => closure.evidence[key] === true).length,
  };
}

export const useCallStore = create<CallState>((set) => ({
  mode: "mock",
  connected: false,
  error: null,
  shell: "standby" as AgentShell,
  summaryReturn: "assist" as SummaryReturn,
  ...emptyCall,

  applyTranscript: (event) => {
    set((state) => {
      const next: Utterance = {
        segment_id: event.segment_id,
        speaker: event.speaker,
        text: event.text,
        ...(event.plain_text === undefined
          ? {}
          : { plain_text: event.plain_text }),
        masked: event.masked,
        is_final: event.is_final,
        utterance_end_ms: event.utterance_end_ms,
      };
      const index = state.utterances.findIndex(
        (item) => item.segment_id === event.segment_id,
      );
      const utterances =
        index === -1
          ? [...state.utterances, next]
          : state.utterances.map((item, i) => (i === index ? next : item));

      const remaining = state.maskingLog.filter(
        (item) => item.segment_id !== event.segment_id,
      );
      const added = event.masked.map((mask, maskIndex) => ({
        id: `${event.segment_id}-${maskIndex}`,
        segment_id: event.segment_id,
        type: mask.type,
        span: mask.span,
        excerpt: sliceByCodepoints(event.text, mask.span[0], mask.span[1]),
        utterance_end_ms: event.utterance_end_ms,
      }));

      return {
        callId: event.call_id,
        utterances,
        maskingLog: [...remaining, ...added],
      };
    });
  },

  applyRecommendation: (incoming, callId, triggerAtMs, fired) => {
    set((state) => {
      const withSource = incoming.filter(hasCardSource);
      const arriving = new Set(withSource.map(cardId));
      const seen = new Set(state.cards.map((item) => cardId(item.card)));
      const added = withSource.filter((card) => !seen.has(cardId(card)));

      // 상담원이 먼저 찾아둔 문서를 자동 추천이 뒤늦게 짚으면 「수동 검색」을 뗀다.
      const promoted = state.cards.map((item) =>
        cardSourceType(item.card) === "manual" && arriving.has(cardId(item.card))
          ? { ...item, card: { ...item.card, source_type: "auto" as const } }
          : item,
      );
      if (added.length === 0) {
        return { callId, cards: promoted, lastFired: fired, cardsLoading: false };
      }
      let cards: PanelCard[] = [
        ...promoted,
        ...added.map((card) => ({
          card,
          trigger_at_ms: triggerAtMs,
          closure: null,
          settled: false,
        })),
      ];
      if (state.closure !== null) {
        const attached = cards.some(
          (item) => item.closure?.closure_type === state.closure?.closure_type,
        );
        if (!attached) {
          cards = withClosure(cards, state.closure);
        }
      }
      return { callId, cards, lastFired: fired, cardsLoading: false };
    });
  },

  startCardsLoading: () => {
    set({ cardsLoading: true });
  },

  applyManualResult: (incoming) => {
    let added = 0;
    set((state) => {
      // 출처 없는 카드는 그리지 않는다 (§2.3 B-6).
      const seen = new Set(state.cards.map((item) => cardId(item.card)));
      const fresh = incoming
        .filter(hasCardSource)
        .map((card) => ({ ...card, source_type: "manual" as const }))
        .filter((card) => !seen.has(cardId(card)));
      added = fresh.length;
      if (fresh.length === 0) {
        return {};
      }
      return {
        cards: [
          ...state.cards,
          ...fresh.map((card) => ({
            card,
            trigger_at_ms: 0,
            closure: null,
            settled: false,
          })),
        ],
      };
    });
    return added;
  },

  applyClosure: (event) => {
    set((state) => ({
      callId: event.call_id,
      closure: event,
      cards: withClosure(state.cards, event),
    }));
  },

  settleClosure: (closureType) => {
    set((state) => ({
      cards: state.cards.map((item) =>
        item.closure?.closure_type === closureType
          ? { ...item, settled: true }
          : item,
      ),
    }));
  },

  logManualSearch: (query, found) => {
    set((state) => ({
      manualSearches: [...state.manualSearches, { query, found }],
    }));
  },

  toggleAdoption: (card) => {
    set((state) => {
      const id = cardId(card);
      const adopted = state.adoptions[id]?.adopted !== true;
      return {
        adoptions: {
          ...state.adoptions,
          [id]: { call_id: state.callId ?? "", card_id: id, adopted },
        },
      };
    });
  },

  endCall: () => {
    set({ phase: "wrapup", connected: false });
  },

  resumeCall: () => {
    set({ phase: "live" });
  },

  setStatus: (mode, connected) => {
    set({ mode, connected, error: null });
  },

  setError: (message) => {
    set({ error: message, connected: false });
  },

  applyTranslation: (transcriptSegmentId, event) => {
    set((state) => ({
      translations: {
        ...state.translations,
        [transcriptSegmentId]: event,
      },
    }));
  },

  applyAgentTts: (transcriptSegmentId, event) => {
    set((state) => ({
      agentTts: {
        ...state.agentTts,
        [transcriptSegmentId]: event,
      },
    }));
  },

  applyCallGuard: (transcriptSegmentId, event) => {
    set((state) => ({
      callGuard: {
        ...state.callGuard,
        [transcriptSegmentId]: event,
      },
    }));
  },

  applyAccentHint: (transcriptSegmentId) => {
    set((state) => ({
      accentHints: {
        ...state.accentHints,
        [transcriptSegmentId]: true,
      },
    }));
  },

  flagBlackConsumer: (callId) => {
    const flag: BlackConsumerFlag = { call_id: callId, flagged_at: Date.now() };
    reportBlackConsumer(flag);
    set({ blackConsumerFlag: flag });
  },

  setTargetLanguage: (lang) => {
    set({ targetLanguage: lang });
  },

  resetCall: () => {
    set({ ...emptyCall, error: null });
  },

  enterAssist: () => {
    set({ shell: "assist" });
  },

  enterStandby: () => {
    set({
      shell: "standby",
      phase: "live",
      summaryReturn: "standby",
    });
  },

  openHistory: (item, options) => {
    const playback = getHistoryPlayback(item.call_id);
    if (playback === null) {
      return;
    }
    set({
      viewMode: "history",
      summaryReturn: options?.returnTo ?? "assist",
      historyCallId: item.call_id,
      historyStartedAt: item.started_at,
      historySegments: playback.page.segments,
      historyTargetLanguage: playback.targetLanguage ?? null,
      historyTranslations: playback.translations,
      historyAgentTts: playback.agentTts,
      historyCallGuard: playback.callGuard,
      historyAccentHints: playback.accentHints,
      historyCards: panelFromScenario(getScenarioById(playback.scenarioId)),
    });
  },

  resumeLive: () => {
    set({
      viewMode: "live",
      historyCallId: null,
      historyStartedAt: null,
      historySegments: [],
      historyTargetLanguage: null,
      historyTranslations: {},
      historyAgentTts: {},
      historyCallGuard: {},
      historyAccentHints: {},
      historyCards: [],
    });
  },
}));
