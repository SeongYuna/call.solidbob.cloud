import type {
  AgentTtsStatus,
  DemoDomain,
  RecommendationBatch,
  RecommendationCard,
  TranscriptEvent,
} from "../../types/contract";

/** 텍스트 안 연속 `*` 구간. 보이는 자리 전부를 마스킹한다. */
export function asteriskSpan(text: string): [number, number] {
  const chars = Array.from(text);
  const start = chars.findIndex((ch) => ch === "*");
  if (start === -1) {
    throw new Error("마스킹할 * 가 없습니다.");
  }
  let end = start;
  while (end < chars.length && chars[end] === "*") {
    end += 1;
  }
  return [start, end];
}

export function utterance(
  callId: string,
  domain: DemoDomain,
  segment_id: string,
  speaker: TranscriptEvent["speaker"],
  text: string,
  utterance_end_ms: number,
  maskType: TranscriptEvent["masked"][number]["type"] | null,
  plain: string | null = null,
): TranscriptEvent {
  return {
    call_id: callId,
    segment_id,
    speaker,
    text,
    ...(plain === null ? {} : { plain_text: plain }),
    masked:
      maskType === null ? [] : [{ type: maskType, span: asteriskSpan(text) }],
    is_final: true,
    utterance_end_ms,
    domain,
  };
}

/** A-5 mock. 상담원 세그먼트마다 TTS 「전송됨」. */
export function agentTtsSent(
  targetLang: AgentTtsStatus["target_lang"],
  segmentIds: readonly string[],
): Record<string, AgentTtsStatus> {
  const out: Record<string, AgentTtsStatus> = {};
  for (const [index, id] of segmentIds.entries()) {
    out[id] = {
      segment_id: (index + 1) * 2,
      target_lang: targetLang,
      status: "sent",
    };
  }
  return out;
}

export function cardBatch(
  callId: string,
  domain: DemoDomain,
  trigger_at_ms: number,
  cards: RecommendationCard[],
): RecommendationBatch {
  return {
    call_id: callId,
    trigger_at_ms,
    internal_latency_ms: 780,
    e2e_latency_ms: 1240,
    domain,
    cards,
  };
}
