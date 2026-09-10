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
  /**
   * J-4 등록 만료 기간(개월) **기본값**. `decisions/205` ⑤가 "만료가 없으면
   * 영구 표시가 된다"고 정한 값 — 원래 코드에 182일(6개월)로 박혀 있던 것을
   * 설정으로 뺐다. 승인 화면에 이 값이 미리 채워지지만, **건마다 다르게**
   * 조정할 수 있다(2026-09-10 — 사안마다 심각도가 다른데 일괄 적용은 안 맞다는
   * 피드백). 전역 기본값은 여기, 개별 조정은 승인 시점·등록 후 연장으로 한다.
   */
  blacklistExpiryMonths: number;
  decideRequest: (
    requestId: string,
    approve: boolean,
    decidedBy: string,
    expiryMonths?: number,
  ) => void;
  releaseEntry: (entryId: string, releasedBy: string, reason: string) => void;
  /** 이미 등록된 건의 만료일을 지금부터 (개월) 뒤로 다시 잡는다 — 연장·단축 둘 다. */
  extendEntry: (entryId: string, months: number) => void;
  setVeteranThresholdYears: (years: number) => void;
  setBlacklistExpiryMonths: (months: number) => void;
}

export const useAdminStore = create<AdminState>((set) => ({
  requests: SEED_REQUESTS,
  entries: SEED_ENTRIES,
  knowledgeGapLog: SEED_KNOWLEDGE_GAP_LOG,
  callGuardLog: SEED_CALL_GUARD_LOG,
  completedCallsTotal: SEED_COMPLETED_CALLS_TOTAL,
  veteranThresholdYears: 3,
  blacklistExpiryMonths: 6,

  // ⚠ 상담원은 pending 까지만 만들 수 있다. 여기서도 pending 이 아닌 요청은
  // 조용히 무시한다 — 반려된 요청을 되살리려면 새 요청을 올려야 한다
  // (`_project/decisions/204`).
  decideRequest: (requestId, approve, decidedBy, expiryMonths) => {
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
      // 이 건에 지정한 기간이 있으면 그걸 쓰고, 없으면 전역 기본값을 쓴다.
      const months = expiryMonths ?? state.blacklistExpiryMonths;
      const expiryDays = Math.round(months * 30);
      const expires = new Date(
        Date.now() + expiryDays * 24 * 60 * 60 * 1000,
      ).toISOString();
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

  // 연장·단축 둘 다 이걸로 한다 — "지금부터 (개월) 뒤" 로 다시 잡는 것이지
  // 기존 만료일에 더하는 것이 아니다. 그래야 관리자가 화면에서 결과 날짜를
  // 바로 예상할 수 있다.
  extendEntry: (entryId, months) => {
    set((state) => ({
      entries: state.entries.map((e) =>
        e.entry_id === entryId && e.released_at === null
          ? {
              ...e,
              expires_at: new Date(
                Date.now() + Math.round(months * 30) * 24 * 60 * 60 * 1000,
              ).toISOString(),
            }
          : e,
      ),
    }));
  },

  setVeteranThresholdYears: (years) => {
    set({ veteranThresholdYears: years });
  },

  setBlacklistExpiryMonths: (months) => {
    set({ blacklistExpiryMonths: months });
  },
}));
