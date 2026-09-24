import { create } from "zustand";
import {
  changeBlacklistEntryExpiry,
  decideBlacklistRequestApi,
  fetchAdminStats,
  fetchBlacklistEntries,
  fetchBlacklistRequests,
  fetchKnowledgeGaps,
  fetchRoutingSetting,
  HubApiError,
  releaseBlacklistEntryApi,
  resolveKnowledgeGap,
  saveRoutingSetting,
  type KnowledgeGapItem,
} from "../lib/api/hubClient";
import { useAuthStore } from "../lib/auth/authStore";
import type { BlacklistEntryItem, BlacklistRequestItem } from "../types/blacklist";

/**
 * 관리자 화면 전용 스토어. `apps/call`의 `callStore.ts`와 더는
 * 공유하지 않는다(2026-09-10, 앱 분리).
 *
 * 2026-09-15(`w4-dashboard-live-contract`) — 승인요청·블랙리스트·현황판 두 칸은
 * 이제 `server`(FastAPI) `/hub/*`를 실제로 부른다(`lib/api/hubClient.ts`).
 * **연결에 실패하면 빈 목록으로 조용히 넘어가지 않는다** — `status`/`error`를
 * 화면이 그대로 보여준다(티켓 완료 조건).
 * 2026-09-16 — `knowledgeGaps`도 실제 계약(`GET /hub/knowledge-gaps`)에 붙였다.
 * `KnowledgeGapTab`을 module/description/status 모양으로 다시 설계해서 가능해졌다.
 */
type LoadStatus = "idle" | "loading" | "ready" | "error";

interface AdminState {
  status: LoadStatus;
  error: string | null;
  requests: BlacklistRequestItem[];
  entries: BlacklistEntryItem[];
  knowledgeGaps: KnowledgeGapItem[];
  callGuardTotal: number;
  completedCallsTotal: number;
  /**
   * `GET /hub/admin-stats`가 준 승인 대기·활성 등록 건수(2026-09-22) — 현황판
   * 전용 스냅샷이다. 사이드바 배지·`NotificationBell`이 쓰는 `AdminPanel.tsx`의
   * `pendingCount`/`activeEntryCount`(요청·등록 목록에서 그때그때 다시 세는
   * 값)와는 다르다 — 그쪽은 승인·해제 직후 바로 갱신돼야 해서 계속 목록에서
   * 센다. 이 값은 `loadAll` 시점의 스냅샷이라 그 사이엔 갱신되지 않는다.
   */
  statsPendingRequests: number;
  statsActiveEntries: number;
  /** 현황판에 "OO시 기준"으로 보여준다. 아직 못 불렀으면 null. */
  statsCountedAt: string | null;
  /**
   * J-5 배정 판정(`decisions/126`·`320`) 집계 — `admin-stats` 응답에는 처음부터
   * 있었지만 콜 미디에이터가 안 불러 전부 0이던 동안은 화면에 렌더하지 않았다.
   * 2026-09-22 배포(call-mediator 0.2.5)로 실제 값이 쌓이기 시작해 현황판에 연다.
   */
  statsRoutingDecisions: number;
  statsRoutingBlacklisted: number;
  statsRoutingFellBack: number;
  /** `decisions/313` — 서버 값(`GET /hub/routing-settings`). `loadAll` 전까지는 로컬 기본값. */
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
    /** 승인 메모는 선택, 반려 사유는 서버 필수(`decisions/316`) — 호출부가 빈 문자열로 부르지 않는다. */
    note?: string,
  ) => Promise<void>;
  releaseEntry: (entryId: string, releasedBy: string, reason: string) => Promise<void>;
  /** `decisions/309` — 연장·단축 실제 API. "지금부터 (개월) 뒤"로 다시 잡는다. 사유 필수. */
  extendEntry: (entryId: string, months: number, reason: string) => Promise<void>;
  setVeteranThresholdYears: (years: number) => Promise<void>;
  setBlacklistExpiryMonths: (months: number) => void;
  /** 되돌리기(resolved→open)도 같은 액션이다 — 서버가 둘 다 허용한다. */
  resolveGap: (gapId: string, status: "open" | "resolved") => Promise<void>;
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
  knowledgeGaps: [],
  callGuardTotal: 0,
  completedCallsTotal: 0,
  statsPendingRequests: 0,
  statsActiveEntries: 0,
  statsCountedAt: null,
  statsRoutingDecisions: 0,
  statsRoutingBlacklisted: 0,
  statsRoutingFellBack: 0,
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
      const [requests, entries, knowledgeGaps, stats, routingSetting] = await Promise.all([
        fetchBlacklistRequests(accessToken),
        fetchBlacklistEntries(accessToken),
        fetchKnowledgeGaps(accessToken),
        fetchAdminStats(accessToken),
        fetchRoutingSetting(accessToken),
      ]);
      set({
        status: "ready",
        error: null,
        requests,
        entries,
        knowledgeGaps,
        callGuardTotal: stats.callGuardFlags,
        completedCallsTotal: stats.callsClosed,
        statsPendingRequests: stats.pendingRequests,
        statsActiveEntries: stats.activeEntries,
        statsCountedAt: stats.countedAt,
        statsRoutingDecisions: stats.routingDecisions,
        statsRoutingBlacklisted: stats.routingBlacklisted,
        statsRoutingFellBack: stats.routingFellBack,
        veteranThresholdYears: routingSetting.veteranYears,
      });
    } catch (error) {
      // 401은 다른 오류와 다르다 — 「다시 시도」를 눌러도 같은 토큰으로 또 401이 난다.
      // 세션을 지우고 로그인 화면(별도 문구)으로 돌려보낸다(w6-admin-stats-wallboard).
      if (error instanceof HubApiError && error.status === 401) {
        await useAuthStore.getState().logout();
        useAuthStore.setState({ error: "세션이 만료되었습니다 — 다시 로그인해 주세요." });
        return;
      }
      set({ status: "error", error: errorMessage(error) });
    }
  },

  // ⚠ 상담원은 pending 까지만 만들 수 있다. 여기서도 pending 이 아닌 요청은
  // 조용히 무시한다 — 반려된 요청을 되살리려면 새 요청을 올려야 한다
  // (`_project/decisions/204`).
  decideRequest: async (requestId, approve, _decidedBy, expiryMonths, note) => {
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
        note,
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

  // `decisions/313` — 다음 배정 판정부터 쓰인다. 저장 성공 응답으로만 상태를 바꾼다
  // (낙관적 갱신을 하면 422 실패 시 화면과 서버 값이 어긋난다).
  setVeteranThresholdYears: async (years) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ error: "로그인이 필요합니다." });
      return;
    }
    try {
      const saved = await saveRoutingSetting(accessToken, years);
      set({ veteranThresholdYears: saved.veteranYears, error: null });
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },

  setBlacklistExpiryMonths: (months) => {
    set({ blacklistExpiryMonths: months });
  },

  resolveGap: async (gapId, status) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) {
      set({ error: "로그인이 필요합니다." });
      return;
    }
    try {
      const resolved = await resolveKnowledgeGap(accessToken, gapId, status);
      set((state) => ({
        knowledgeGaps: state.knowledgeGaps.map((g) =>
          g.gap_id === resolved.gap_id ? { ...g, status: resolved.status } : g,
        ),
        error: null,
      }));
    } catch (error) {
      set({ error: errorMessage(error) });
    }
  },
}));
