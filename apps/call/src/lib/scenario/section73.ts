/**
 * 7.3절 v2 JSON 예시를 그대로 옮긴 값.
 * 프론트가 데모용 발화·카드를 지어내지 않는다 (CLAUDE.md 2번).
 */
import type {
  ClosureEvent,
  RecommendationBatch,
  TranscriptEvent,
} from "../../types/contract";

export const SECTION_73_TRANSCRIPT: TranscriptEvent = {
  call_id: "c_001",
  segment_id: "seg_0031",
  speaker: "customer",
  text: "카드번호는 **** 입니다",
  masked: [{ type: "P2", span: [6, 10] }],
  is_final: true,
  utterance_end_ms: 3100,
};

export const SECTION_73_RECOMMENDATION: RecommendationBatch = {
  fired: true,
  call_id: "c_001",
  trigger_at_ms: 3150,
  cards: [
    {
      title: "프로모션 할인 적용 시점 안내",
      summary: "신규 가입 할인은 가입 다음 달 청구서부터 반영됩니다.",
      source: { doc_id: "TERM-3.2", title: "요금제약관 제3조 2항" },
      similarity_score: 0.87,
    },
  ],
  internal_latency_ms: 780,
};

/** `server/apps/hub/app/dtos/closure_verdict_dto.py`의 7.3절 rev.5 예시를 그대로 옮겼다(`decisions/305`). */
export const SECTION_73_CLOSURE: ClosureEvent = {
  call_id: "c_001",
  procedure: "DASAN-TERM-4.3",
  procedure_title: "주민등록초본 발급",
  evidence: { 신분증: false },
  verdict: "incomplete",
  missing: ["신분증"],
  source: { doc_id: "DASAN-TERM-4.3", title: "주민등록초본 발급 — 필요서류" },
  detected: true,
};
