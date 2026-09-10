import { create } from "zustand";
import {
  SEED_CALL_GUARD_LOG,
  SEED_COMPLETED_CALLS_TOTAL,
  SEED_ENTRIES,
  SEED_KNOWLEDGE_GAP_LOG,
  SEED_REQUESTS,
} from "../mock/adminFixtures";
import type {
  BlacklistEntryItem,
  BlacklistRequestItem,
  CallGuardLogEntry,
  KnowledgeGapEntry,
} from "../types/blacklist";

/**
 * 관리자 화면 전용 스토어. `apps/dashboard`의 `callStore.ts`와 더는
 * 공유하지 않는다(2026-09-10, 앱 분리) — 지금은 mock 시드 데이터로
 * 시작하고, 실제 백엔드가 붙으면 액션 안쪽을 API 호출로 바꾼다. 화면
 * 컴포넌트(`components/admin/*`)는 그대로 두면 된다.
 */
interface AdminState {
  requests: BlacklistRequestItem[];
  entries: BlacklistEntryItem[];
  knowledgeGapLog: KnowledgeGapEntry[];
  callGuardLog: CallGuardLogEntry[];
  completedCallsTotal: number;
  veteranThresholdYears: number;
  decideRequest: (requestId: string, approve: boolean, decidedBy: string) => void;
  releaseEntry: (entryId: string, releasedBy: string, reason: string) => void;
  setVeteranThresholdYears: (years: number) => void;
}

export const useAdminStore = create<AdminState>((set) => ({
  requests: SEED_REQUESTS,
  entries: SEED_ENTRIES,
  knowledgeGapLog: SEED_KNOWLEDGE_GAP_LOG,
  callGuardLog: SEED_CALL_GUARD_LOG,
  completedCallsTotal: SEED_COMPLETED_CALLS_TOTAL,
  veteranThresholdYears: 3,

  // ⚠ 상담원은 pending 까지만 만들 수 있다. 여기서도 pending 이 아닌 요청은
  // 조용히 무시한다 — 반려된 요청을 되살리려면 새 요청을 올려야 한다
  // (`_project/decisions/204`).
  decideRequest: (requestId, approve, decidedBy) => {
    set((state) => {
      const target = state.requests.find((r) => r.request_id === requestId);
      if (!target || target.status !== "pending") {
        return {};
      }
      const decidedAt = new Date().toISOString();
      const requests = state.requests.map((r) =>
        r.request_id === requestId
          ? {
              ...r,
              status: approve ? ("approved" as const) : ("rejected" as const),
              decided_by: decidedBy,
              decided_at: decidedAt,
            }
          : r,
      );
      if (!approve) {
        return { requests };
      }
      const already = state.entries.some(
        (e) => e.customer_ref === target.customer_ref && e.released_at === null,
      );
      // 만료 기본값 6개월(`decisions/205` ⑤) — 재서 고른 값이 아니라 기본값이다.
      const expires = new Date(Date.now() + 182 * 24 * 60 * 60 * 1000).toISOString();
      return {
        requests,
        entries: already
          ? state.entries
          : [
              {
                entry_id: `ent-${Date.now()}`,
                customer_ref: target.customer_ref,
                request_id: target.request_id,
                approved_at: decidedAt,
                expires_at: expires,
                released_at: null,
                released_by: null,
                release_reason: null,
                // ⚠ 요청 사유를 복사하지 않는다 — 같은 개인정보가 두 벌이 된다.
                note: null,
              },
              ...state.entries,
            ],
      };
    });
  },

  // 행을 지우지 않고 released_at 을 채운다 — 지우면 「왜 풀렸는지」가 사라진다
  // (절대 원칙 8).
  releaseEntry: (entryId, releasedBy, reason) => {
    set((state) => ({
      entries: state.entries.map((e) =>
        e.entry_id === entryId && e.released_at === null
          ? {
              ...e,
              released_at: new Date().toISOString(),
              released_by: releasedBy,
              release_reason: reason,
            }
          : e,
      ),
    }));
  },

  setVeteranThresholdYears: (years) => {
    set({ veteranThresholdYears: years });
  },
}));
