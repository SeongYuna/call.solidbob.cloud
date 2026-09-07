/**
 * GET /hub/calls 목록 API 연결 전 임시 mock.
 * 자막 페이지는 GET /hub/calls/{call_id}/transcript (`TranscriptPage`) 형태.
 * 목록은 mock 시나리오와 같은 데이터다 — 상담기록 칩이 시나리오 칩을 겸한다.
 */
import type {
  AgentTtsStatus,
  CallGuardFlag,
  CallHistoryItem,
  CallWrapUp,
  Domain,
  TranscriptPage,
  TranslatedUtterance,
} from "../types/contract";
import type { TargetLanguage } from "../lib/language/languageMeta";
import {
  getScenarioById,
  MOCK_SCENARIO_FLAG,
  type MockScenarioId,
} from "./scenarios";
import type { MockScenario } from "./scenarios/types";
import { mockAgentTts, mockCustomerTranslation } from "../lib/translation/mockSource";
import { DEFAULT_LOCAL_RESOURCES } from "./localResources";
import { sentimentFromScenario } from "./sentiment";

export interface CallHistoryRow {
  item: CallHistoryItem;
  scenarioId: MockScenarioId;
  langFlag: string;
}

interface HistoryRecord extends CallHistoryRow {
  page: TranscriptPage;
  translations: Record<string, TranslatedUtterance>;
  agentTts: Record<string, AgentTtsStatus>;
  callGuard: Record<string, CallGuardFlag>;
  accentHints: Record<string, true>;
  wrapUp: CallWrapUp;
}

function item(
  callId: string,
  started_at: string,
  domain: Domain,
  inquiry_type: string,
  hex: string,
  targetLanguage?: TargetLanguage,
): CallHistoryItem {
  return {
    call_id: callId,
    started_at,
    domain,
    inquiry_type,
    customer_ref: `고객 #${hex}`,
    targetLanguage,
  };
}

function playbackFromScenario(
  callId: string,
  scenario: MockScenario,
): Pick<
  HistoryRecord,
  "page" | "translations" | "agentTts" | "callGuard" | "accentHints"
> {
  const translations: Record<string, TranslatedUtterance> = {};
  const agentTts: Record<string, AgentTtsStatus> = {};
  const callGuard: Record<string, CallGuardFlag> = {};
  const accentHints: Record<string, true> = {};
  const segments = scenario.transcripts.map((event, index) => {
    const key = String(index + 1);
    const translation = mockCustomerTranslation(scenario, event.segment_id);
    if (translation !== undefined) {
      translations[key] = translation;
    }
    const tts = mockAgentTts(scenario, event.segment_id);
    if (tts !== undefined) {
      agentTts[key] = tts;
    }
    const guard = scenario.callGuard?.[event.segment_id];
    if (guard !== undefined) {
      callGuard[key] = guard;
    }
    if (scenario.accentRecognition === true && event.speaker === "customer") {
      accentHints[key] = true;
    }
    return {
      segment_id: index + 1,
      speaker: event.speaker,
      text: event.text,
      ...(event.plain_text === undefined ? {} : { plain_text: event.plain_text }),
      masked: event.masked,
      is_final: event.is_final,
      utterance_end_ms: event.utterance_end_ms,
    };
  });
  return {
    page: {
      call_id: callId,
      segments,
      total: segments.length,
      limit: segments.length,
      offset: 0,
    },
    translations,
    agentTts,
    callGuard,
    accentHints,
  };
}

function completeWrapUp(callId: string, scenario: MockScenario): CallWrapUp {
  return {
    call_id: callId,
    ...scenario.wrapUp,
    local_resources:
      scenario.wrapUp.local_resources !== undefined &&
      scenario.wrapUp.local_resources.length > 0
        ? scenario.wrapUp.local_resources
        : [...DEFAULT_LOCAL_RESOURCES],
    sentiment: sentimentFromScenario(scenario, callId),
  };
}

function record(
  scenarioId: MockScenarioId,
  started_at: string,
  inquiry_type: string,
  hex: string,
): HistoryRecord {
  const scenario = getScenarioById(scenarioId);
  const callId = scenario.transcripts[0]?.call_id ?? `c_hist_${scenarioId}`;
  const played = playbackFromScenario(callId, scenario);
  return {
    item: item(
      callId,
      started_at,
      "dasan",
      inquiry_type,
      hex,
      scenario.targetLanguage,
    ),
    scenarioId,
    langFlag: MOCK_SCENARIO_FLAG[scenarioId],
    wrapUp: completeWrapUp(callId, scenario),
    ...played,
  };
}

const HISTORY_META: Record<
  MockScenarioId,
  { started_at: string; inquiry_type: string; hex: string }
> = {
  "vi-deungbon": {
    started_at: "2026-08-28T08:44:00+09:00",
    inquiry_type: "주민등록등본 재발급 절차",
    hex: "e3c7",
  },
  "en-transit": {
    started_at: "2026-08-27T19:03:00+09:00",
    inquiry_type: "노선·환승 안내 원칙",
    hex: "09df",
  },
  "ja-sewer": {
    started_at: "2026-08-26T14:18:00+09:00",
    inquiry_type: "생활하수도 관련 문의",
    hex: "5a18",
  },
  "zh-covid": {
    started_at: "2026-08-25T12:30:00+09:00",
    inquiry_type: "코로나19 관련 상담",
    hex: "a4b2",
  },
  "th-admin": {
    started_at: "2026-08-25T09:12:00+09:00",
    inquiry_type: "행정 처리 기한",
    hex: "7c91",
  },
  "ko-masking": {
    started_at: "2026-08-28T16:20:00+09:00",
    inquiry_type: "민원 접수 본인확인",
    hex: "b8e1",
  },
  "ko-callguard": {
    started_at: "2026-08-31T09:12:00+09:00",
    inquiry_type: "시설 민원 · 콜가드",
    hex: "c6a1",
  },
  "ko-grant-delay": {
    started_at: "2026-08-31T15:20:00+09:00",
    inquiry_type: "고객 응대 · 콜가드 감지",
    hex: "d9c2",
  },
  "ko-accent": {
    started_at: "2026-08-31T10:04:00+09:00",
    inquiry_type: "교통약자 이동 지원 · 억양",
    hex: "a5b2",
  },
};

const RECORDS: readonly HistoryRecord[] = (
  Object.keys(HISTORY_META) as MockScenarioId[]
).map((id) => {
  const meta = HISTORY_META[id];
  return record(id, meta.started_at, meta.inquiry_type, meta.hex);
});

function sorted(): HistoryRecord[] {
  return [...RECORDS].sort((a, b) =>
    a.item.started_at < b.item.started_at ? 1 : -1,
  );
}

/** GET /hub/calls 목록 API 연결 전 임시 mock */
export function listCallHistory(): CallHistoryItem[] {
  return sorted().map((row) => row.item);
}

export function listCallHistoryRows(): CallHistoryRow[] {
  return sorted().map(({ item, scenarioId, langFlag }) => ({
    item,
    scenarioId,
    langFlag,
  }));
}

export function getHistoryPlayback(callId: string): {
  page: TranscriptPage;
  translations: Record<string, TranslatedUtterance>;
  agentTts: Record<string, AgentTtsStatus>;
  callGuard: Record<string, CallGuardFlag>;
  accentHints: Record<string, true>;
  scenarioId: MockScenarioId;
  targetLanguage: TargetLanguage | undefined;
  wrapUp: CallWrapUp;
} | null {
  const found = RECORDS.find((row) => row.item.call_id === callId);
  if (found === undefined) {
    return null;
  }
  return {
    page: found.page,
    translations: found.translations,
    agentTts: found.agentTts,
    callGuard: found.callGuard,
    accentHints: found.accentHints,
    scenarioId: found.scenarioId,
    targetLanguage: found.item.targetLanguage,
    wrapUp: found.wrapUp,
  };
}

/** GET /hub/calls/{call_id}/transcript 연결 전 임시 mock */
export function getCallTranscript(callId: string): TranscriptPage | null {
  return getHistoryPlayback(callId)?.page ?? null;
}
