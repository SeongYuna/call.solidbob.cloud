/**
 * 관리자 화면 mock 시드 데이터. 실제 백엔드 API가 붙기 전까지 화면을
 * 비어 보이지 않게 하는 예시일 뿐이다 — `apps/call`의 실시간 상태에서
 * 온 것이 아니다(2026-09-10, 앱 분리로 두 곳이 더는 상태를 공유하지 않는다).
 */
import type {
  BlacklistEntryItem,
  BlacklistRequestItem,
  KnowledgeGapEntry,
} from "../types/blacklist";

export const SEED_REQUESTS: BlacklistRequestItem[] = [
  {
    request_id: "req-seed-1",
    call_id: "c_seed_1",
    customer_ref: "hmac_seed_1",
    display_hint: "****3841",
    requested_by: "조서희",
    reason: "상담 도중 반복적인 욕설과 위협이 있었습니다.",
    // ⚠ P1~P7 코드는 화면에 내지 않는다(`.claude/rules/dashboard.md` §2) —
    // 마스킹된 자막이라도 패턴 코드를 그대로 노출하지 않는다.
    context_excerpt: "고객: 이거 안 해주면 알아서 해\n고객: 계속 이따위로 할 거야",
    evidence: {
      call_duration_s: 612,
      insult_count: 4,
      threat_count: 2,
      sexual_count: 0,
      distress_count: 0,
      temperature_outliers: 3,
    },
    status: "pending",
    requested_at: "2026-09-10T09:12:00+09:00",
    decided_by: null,
    decided_at: null,
    evidence_snapshot_at: "2026-09-10T09:12:00+09:00",
  },
];

export const SEED_ENTRIES: BlacklistEntryItem[] = [
  {
    entry_id: "ent-seed-1",
    customer_ref: "hmac_seed_2",
    request_id: "req-seed-0",
    approved_at: "2026-09-05T14:00:00+09:00",
    expires_at: "2027-03-04T14:00:00+09:00",
    released_at: null,
    released_by: null,
    release_reason: null,
    note: "폭언 반복 확인 후 승인",
  },
  // 재등록 예시 — 같은 customer_ref로 예전에 등록됐다 해제된 뒤 다시 등록됐다.
  // EntriesTab의 "기존(재범)" 필터가 이 customer_ref를 잡는지 보여주는 mock 데이터다.
  {
    entry_id: "ent-seed-2-first",
    customer_ref: "hmac_seed_3",
    request_id: "req-seed-2a",
    approved_at: "2026-07-01T10:00:00+09:00",
    expires_at: "2026-08-01T10:00:00+09:00",
    released_at: "2026-08-01T10:00:00+09:00",
    released_by: "정성윤",
    release_reason: "만료 후 자동 해제",
    note: "1차 등록",
  },
  {
    entry_id: "ent-seed-2-second",
    customer_ref: "hmac_seed_3",
    request_id: "req-seed-2b",
    approved_at: "2026-09-08T11:30:00+09:00",
    expires_at: "2027-03-08T11:30:00+09:00",
    released_at: null,
    released_by: null,
    release_reason: null,
    note: "해제 뒤 재범으로 재등록",
  },
];

export const SEED_KNOWLEDGE_GAP_LOG: KnowledgeGapEntry[] = [
  { call_id: "c_seed_2", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-09T10:00:00+09:00" },
  { call_id: "c_seed_3", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-09T15:30:00+09:00" },
  { call_id: "c_seed_4", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-10T08:20:00+09:00" },
  { call_id: "c_seed_5", query: "체류지 변경 신고", found: false, logged_at: "2026-09-09T11:00:00+09:00" },
  { call_id: "c_seed_6", query: "주민등록등본 발급 수수료", found: true, logged_at: "2026-09-09T12:00:00+09:00" },
];

