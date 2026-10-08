// Requirement: F-3
/**
 * 고객 브리핑 카드(F-3) 다섯 상태 미리보기 — 실서버 없이 `?briefing=<상태>` 로 연다.
 *
 * 응답은 서버 와이어 형식(값이 전부 문자열) 그대로 두고 `parseCustomerBriefing` 을 거친다 —
 * 미리보기가 파서를 건너뛰면 실제 응답에서만 깨지는 경우를 놓친다.
 * 내용은 전부 지어낸 예시다. 번호·이름 같은 고객 식별 정보는 넣지 않는다(서버도 주지 않는다).
 */
import { parseCustomerBriefing, type CustomerBriefing } from "../lib/api/coreClient";

export type BriefingPreview = "ready" | "ready-rule" | "first_contact" | "unidentified" | "failed" | "loading";

const PREVIEWS: readonly BriefingPreview[] = [
  "ready",
  "ready-rule",
  "first_contact",
  "unidentified",
  "failed",
  "loading",
];

/** 주소창의 `?briefing=` 값. 없거나 모르는 값이면 null(미리보기 아님). */
export function readBriefingPreview(search: string = window.location.search): BriefingPreview | null {
  const value = new URLSearchParams(search).get("briefing");
  return value !== null && PREVIEWS.includes(value as BriefingPreview) ? (value as BriefingPreview) : null;
}

const EMPTY_SIGNALS = { open_follow_ups: "0", call_guard_categories: [], blacklisted: "false" };

const WIRE: Record<"ready" | "ready-rule" | "first_contact" | "unidentified", unknown> = {
  ready: {
    call_id: "preview-briefing-ready",
    status: "ready",
    prior_call_count: "2",
    purpose: {
      category: "서류 보완",
      text: "지난 통화에서 안내한 위임장을 준비하다 막혀 다시 건 것으로 보입니다",
      source: "model",
    },
    briefing_lines: [
      "10-05 통화에서 전입신고 대리 접수에 필요한 서류를 안내받았습니다",
      "위임장 서식을 어디서 받는지 다시 확인하겠다고 하고 통화를 마쳤습니다",
      "10-02 통화는 주차 과태료 납부 방법 문의였습니다",
    ],
    evidence: [
      {
        call_id: "preview-prev-2",
        started_at: "2026-10-05T14:02:00+09:00",
        inquiry_type: "일반행정",
        summary_confirmed: "true",
        incomplete_procedures: ["DASAN-TERM-4.1"],
      },
      {
        call_id: "preview-prev-1",
        started_at: "2026-10-02T10:41:00+09:00",
        inquiry_type: "교통",
        summary_confirmed: "false",
        incomplete_procedures: [],
      },
    ],
    signals: { open_follow_ups: "1", call_guard_categories: ["insult"], blacklisted: "false" },
    generated_at: "2026-10-08T09:00:00+09:00",
  },
  "ready-rule": {
    call_id: "preview-briefing-rule",
    status: "ready",
    prior_call_count: "1",
    purpose: {
      category: "후속 확인",
      text: "지난 통화에서 마치지 않은 후속조치가 있어 그 진행을 확인하려는 것으로 보입니다",
      source: "rule",
    },
    briefing_lines: ["10-06 통화에서 하수 악취 민원을 접수했고 현장 확인 결과를 안내하기로 했습니다"],
    evidence: [
      {
        call_id: "preview-prev-3",
        started_at: "2026-10-06T16:20:00+09:00",
        inquiry_type: "환경",
        summary_confirmed: "true",
        incomplete_procedures: [],
      },
    ],
    signals: { open_follow_ups: "1", call_guard_categories: [], blacklisted: "false" },
    generated_at: "2026-10-08T09:00:00+09:00",
  },
  first_contact: {
    call_id: "preview-briefing-first",
    status: "first_contact",
    prior_call_count: "0",
    purpose: null,
    briefing_lines: [],
    evidence: [],
    signals: EMPTY_SIGNALS,
    generated_at: "2026-10-08T09:00:00+09:00",
  },
  unidentified: {
    call_id: "preview-briefing-unidentified",
    status: "unidentified",
    prior_call_count: "0",
    purpose: null,
    briefing_lines: [],
    evidence: [],
    signals: EMPTY_SIGNALS,
    generated_at: "2026-10-08T09:00:00+09:00",
  },
};

/** 미리보기 상태 → 카드가 받을 값. `failed` 는 null(카드 없음), `loading` 은 `"loading"`. */
export function briefingPreviewValue(preview: BriefingPreview): CustomerBriefing | null | "loading" {
  if (preview === "loading") {
    return "loading";
  }
  if (preview === "failed") {
    return null;
  }
  return parseCustomerBriefing(WIRE[preview]);
}
