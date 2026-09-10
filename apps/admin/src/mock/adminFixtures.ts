/**
 * 관리자 화면 mock 시드 데이터. 실제 백엔드 API가 붙기 전까지 화면을
 * 비어 보이지 않게 하는 예시일 뿐이다 — `apps/dashboard`의 실시간 상태에서
 * 온 것이 아니다(2026-09-10, 앱 분리로 두 곳이 더는 상태를 공유하지 않는다).
 */
import type {
  BlacklistEntryItem,
  BlacklistRequestItem,
  CallGuardLogEntry,
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
    context_excerpt:
      "고객: 이거 안 해주면 [P4] 알아서 해\n고객: 계속 이따위로 할 거야",
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
];

export const SEED_KNOWLEDGE_GAP_LOG: KnowledgeGapEntry[] = [
  { call_id: "c_seed_2", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-09T10:00:00+09:00" },
  { call_id: "c_seed_3", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-09T15:30:00+09:00" },
  { call_id: "c_seed_4", query: "외국인 등록증 재발급", found: false, logged_at: "2026-09-10T08:20:00+09:00" },
  { call_id: "c_seed_5", query: "체류지 변경 신고", found: false, logged_at: "2026-09-09T11:00:00+09:00" },
  { call_id: "c_seed_6", query: "주민등록등본 발급 수수료", found: true, logged_at: "2026-09-09T12:00:00+09:00" },
];

export const SEED_CALL_GUARD_LOG: CallGuardLogEntry[] = [
  { call_id: "c_seed_1", category: "욕설", detected_at: "2026-09-10T09:05:00+09:00" },
  { call_id: "c_seed_1", category: "위협", detected_at: "2026-09-10T09:08:00+09:00" },
  { call_id: "c_seed_7", category: "폭언", detected_at: "2026-09-08T16:00:00+09:00" },
];

export const SEED_COMPLETED_CALLS_TOTAL = 24;
