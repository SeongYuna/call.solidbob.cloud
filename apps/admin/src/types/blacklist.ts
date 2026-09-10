/**
 * J — 콜 라우팅 보호(`_project/decisions/204`) 계약. `apps/dashboard`의
 * `types/contract.ts`에서 관리자 화면이 쓰는 부분만 옮겼다.
 *
 * ⚠ 2026-09-10 — 두 앱을 완전히 분리하면서 타입을 일부러 따로 둔다. 실제
 * 백엔드 API가 붙으면 그쪽이 정본이 되고, 이 파일은 서버 응답 스키마에 맞춰
 * 독립적으로 갱신한다 — `apps/dashboard`와 같은 파일을 공유하지 않는다.
 */

export type BlacklistStatus = "pending" | "approved" | "rejected";

/**
 * 관리자가 **통화를 다시 듣지 않고** 판단할 수 있게 싣는 근거.
 * ⚠ 전부 셀 수 있는 건수다 — 위험도 점수를 만들지 않는다(부록 A-1).
 */
export interface BlacklistEvidence {
  call_duration_s: number;
  insult_count: number;
  threat_count: number;
  sexual_count: number;
  /** ⚠ 블랙리스트 사유가 아니다(`decisions/205` ④) — 위기 신호는 전환 근거에서 뺀다. */
  distress_count: number;
  /** D-5 통화 온도 이상 구간 수(`decisions/203`). 점수가 아니라 건수다. */
  temperature_outliers: number;
}

export interface BlacklistRequestItem {
  request_id: string;
  call_id: string;
  /** ⚠ 전화번호의 HMAC. 평문이 아니다(`decisions/205` ③). */
  customer_ref: string;
  display_hint: string;
  requested_by: string;
  reason: string;
  /** ⚠ 마스킹된 자막이다. 원문이 아니다 — DASAN-MANUAL-5.5 · C-5. */
  context_excerpt: string;
  evidence: BlacklistEvidence;
  status: BlacklistStatus;
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  evidence_snapshot_at: string;
}

/**
 * 등록 **에피소드** 1건. 「고객 1명 = 1행」이 아니다(`decisions/205` ②).
 * ⚠ DB `blacklist_entry` 테이블엔 `display_hint`가 없다 — 표시 힌트는
 * 요청에만 있고, `request_id`로 찾아 붙인다(2026-09-09 ERD 대조로 발견).
 */
export interface BlacklistEntryItem {
  entry_id: string;
  customer_ref: string;
  request_id: string;
  approved_at: string;
  expires_at: string;
  released_at: string | null;
  released_by: string | null;
  release_reason: string | null;
  note: string | null;
}

/** 지식베이스 갭 관리 뷰용. */
export interface KnowledgeGapEntry {
  call_id: string;
  query: string;
  found: boolean;
  logged_at: string;
}

/** 현황판 콜가드 누적 카운트용. */
export interface CallGuardLogEntry {
  call_id: string;
  category: "폭언" | "욕설" | "위협";
  detected_at: string;
}
