import { create } from "zustand";
import {
  changeBlacklistEntryExpiry,
  decideBlacklistRequestApi,
  fetchBlacklistEntries,
  fetchBlacklistRequests,
  fetchCallGuardFlagTotal,
  fetchCallListTotal,
  HubApiError,
  releaseBlacklistEntryApi,
} from "../lib/api/hubClient";
import { useAuthStore } from "../lib/auth/authStore";
import { SEED_KNOWLEDGE_GAP_LOG } from "../mock/adminFixtures";
import type {
  BlacklistEntryItem,
  BlacklistRequestItem,
  KnowledgeGapEntry,
} from "../types/blacklist";

/**
 * 관리자 화면 전용 스토어. `apps/call`의 `callStore.ts`와 더는
 * 공유하지 않는다(2026-09-10, 앱 분리).
 *
 * 2026-09-15(`w4-dashboard-live-contract`) — 승인요청·블랙리스트·현황판 두 칸은
 * 이제 `server`(FastAPI) `/hub/*`를 실제로 부른다(`lib/api/hubClient.ts`).
 * **연결에 실패하면 빈 목록으로 조용히 넘어가지 않는다** — `status`/`error`를
 * 화면이 그대로 보여준다(티켓 완료 조건). `knowledgeGapLog`는 아직 mock이다 —
 * 실제 계약(`GET /hub/knowledge-gaps`)이 `{module, description, status}`라
 * 지금 화면의 `{query, found}` 집계와 모양이 달라 `KnowledgeGapTab`을 다시
 * 설계하기 전까지는 연결하지 않는다(`hubClient.ts`의 `fetchKnowledgeGaps` 참고).
 */
type LoadStatus = "idle" | "loading" | "ready" | "error";

interface AdminState {
  status: LoadStatus;
  error: string | null;
  requests: BlacklistRequestItem[];
  entries: BlacklistEntryItem[];
  knowledgeGapLog: KnowledgeGapEntry[];
  callGuardTotal: number;
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
  /** 로그인 직후 한 번 부른다(`AdminPanel`). 실패해도 예전 값은 지우지 않는다. */
  loadAll: () => Promise<void>;
  decideRequest: (
    requestId: string,
    approve: boolean,
    decidedBy: string,
    expiryMonths?: number,
  ) => Promise<void>;
  releaseEntry: (entryId: string, releasedBy: string, reason: string) => Promise<void>;
  /** `decisions/309` — 연장·단축 실제 API. "지금부터 (개월) 뒤"로 다시 잡는다. 사유 필수. */
  extendEntry: (entryId: string, months: number, reason: string) => Promise<void>;
  setVeteranThresholdYears: (years: number) => void;
  setBlacklistExpiryMonths: (months: number) => void;
}

function errorMessage(error: unknown): string {
  return error instanceof HubApiError || error instanceof Error
    ? error.message
    : "알 수 없는 오류";
}

export const useAdminStore = create<AdminState>((set, get) => ({
  status: "idle",
  error: null,
  requests: [],
  entries: [],
  knowledgeGapLog: SEED_KNOWLEDGE_GAP_LOG,
  callGuardTotal: 0,
  completedCallsTotal: 0,
  veteranThresholdYears: 3,
  blacklistExpiryMonths: 6,

  loadAll: async () => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ status: "error", error: "로그인이 필요합니다." });
      return;
    }
    set({ status: "loading", error: null });
    try {
      const [requests, entries, callGuardTotal, completedCallsTotal] = await Promise.all([
        fetchBlacklistRequests(accessToken),
        fetchBlacklistEntries(accessToken),
        fetchCallGuardFlagTotal(accessToken),
        fetchCallListTotal(),
      ]);
      set({ status: "ready", error: null, requests, entries, callGuardTotal, completedCallsTotal });
    } catch (error) {
      set({ status: "error", error: errorMessage(error) });
    }
  },

  // ⚠ 상담원은 pending 까지만 만들 수 있다. 여기서도 pending 이 아닌 요청은
  // 조용히 무시한다 — 반려된 요청을 되살리려면 새 요청을 올려야 한다
  // (`_project/decisions/204`).
  decideRequest: async (requestId, approve, _decidedBy, expiryMonths) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ error: "로그인이 필요합니다." });
      return;
    }
    const target = get().requests.find((r) => r.request_id === requestId);
    if (!target || target.status !== "pending") {
      return;
    }
    const months = expiryMonths ?? get().blacklistExpiryMonths;
    try {
      // decided_by 는 본문이 아니라 로그인한 관리자에게서 온다 — `_decidedBy`는
      // 화면 표시용 인자일 뿐, 서버가 응답에 실제 값을 채워 돌려준다.
      const decided = await decideBlacklistRequestApi(
        accessToken,
        requestId,
        approve,
        approve ? Math.round(months * 30) : undefined,
      );
      set((state) => ({
        requests: state.requests.map((r) => (r.request_id === requestId ? decided : r)),
        error: null,
      }));
      if (approve) {
        // 결정 응답에는 새로 생긴 등록 행이 없다 — 목록을 다시 받는다.
        const entries = await fetchBlacklistEntries(accessToken);
        set({ entries });
      }
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },

  // 행을 지우지 않고 released_at 을 채운다 — 지우면 「왜 풀렸는지」가 사라진다
  // (절대 원칙 8).
  releaseEntry: async (entryId, _releasedBy, reason) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ error: "로그인이 필요합니다." });
      return;
    }
    try {
      const released = await releaseBlacklistEntryApi(accessToken, entryId, reason);
      set((state) => ({
        entries: state.entries.map((e) => (e.entry_id === entryId ? released : e)),
        error: null,
      }));
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },

  // 연장·단축 둘 다 이걸로 한다 — "지금부터 (개월) 뒤" 로 다시 잡는 것이지
  // 기존 만료일에 더하는 것이 아니다. 그래야 관리자가 화면에서 결과 날짜를
  // 바로 예상할 수 있다. 서버가 1~365일(`MAX_EXPIRES_IN_DAYS`)로 제한한다.
  extendEntry: async (entryId, months, reason) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ error: "로그인이 필요합니다." });
      return;
    }
    try {
      const { entry } = await changeBlacklistEntryExpiry(
        accessToken,
        entryId,
        Math.round(months * 30),
        reason,
      );
      set((state) => ({
        entries: state.entries.map((e) => (e.entry_id === entryId ? entry : e)),
        error: null,
      }));
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },

  setVeteranThresholdYears: (years) => {
    set({ veteranThresholdYears: years });
  },

  setBlacklistExpiryMonths: (months) => {
    set({ blacklistExpiryMonths: months });
  },
}));
