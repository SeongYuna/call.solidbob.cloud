/**
 * `server`(FastAPI) `/hub/*` 관리자 전용 호출. 티켓 `w4-dashboard-live-contract`.
 *
 * 전부 `Authorization: Bearer <access_token>`이 필요하다(`admin_auth`, `require_admin`) —
 * 토큰은 `lib/auth/authStore.ts`에서 받아 호출부가 넘긴다. `apiBaseUrl()`은
 * `authApi.ts`와 같은 값을 쓴다 — admin_auth 도 hub 도 같은 FastAPI 프로세스다.
 *
 * ⚠ 값은 전부 문자열로 온다(`_types.StrField`, 7.3절 계약 전체 규칙) — 여기서
 * number/boolean으로 되돌린다.
 */
import { apiBaseUrl } from "../auth/authApi";
import type { BlacklistEntryItem, BlacklistEvidence, BlacklistRequestItem } from "../../types/blacklist";

export class HubApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
  ) {
    super(message);
    this.name = "HubApiError";
  }
}

function toNum(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    throw new HubApiError(`숫자 필드에 예상 밖 값이 왔다: ${JSON.stringify(value)}`, null);
  }
  return n;
}

async function authedRequest<T>(path: string, accessToken: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "1",
        Authorization: `Bearer ${accessToken}`,
        ...init?.headers,
      },
    });
  } catch (error) {
    throw new HubApiError(
      error instanceof Error ? `서버에 연결하지 못했다: ${error.message}` : "서버에 연결하지 못했다.",
      null,
    );
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message =
      (detail !== null && typeof detail === "object" && "detail" in detail && typeof detail.detail === "string"
        ? detail.detail
        : null) ?? `요청이 실패했다 (${response.status})`;
    throw new HubApiError(message, response.status);
  }
  return (await response.json()) as T;
}

function authedGet<T>(path: string, accessToken: string): Promise<T> {
  return authedRequest<T>(path, accessToken, { method: "GET" });
}

function authedPost<T>(path: string, accessToken: string, body: unknown): Promise<T> {
  return authedRequest<T>(path, accessToken, { method: "POST", body: JSON.stringify(body) });
}

// ── 블랙리스트 요청·등록 wire 모양 (둘 다 `_types.StrField` 규칙) ──────────

interface BlacklistEvidenceWire {
  call_duration_s: string;
  insult_count: string;
  threat_count: string;
  sexual_count: string;
  temperature_outliers: string;
}

interface BlacklistRequestItemWire {
  request_id: string;
  call_id: string;
  customer_ref: string;
  display_hint: string | null;
  requested_by: string;
  reason: string;
  context_excerpt: string;
  evidence: BlacklistEvidenceWire;
  status: string;
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  evidence_snapshot_at: string;
}

interface BlacklistEntryItemWire {
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

function toEvidence(wire: BlacklistEvidenceWire): BlacklistEvidence {
  return {
    call_duration_s: toNum(wire.call_duration_s),
    insult_count: toNum(wire.insult_count),
    threat_count: toNum(wire.threat_count),
    sexual_count: toNum(wire.sexual_count),
    // ⚠ 서버는 저장·응답하지 않는다(`decisions/205` ④) — 화면 전용 값이라 채울 수 없다.
    distress_count: 0,
    temperature_outliers: toNum(wire.temperature_outliers),
  };
}

function toRequestItem(wire: BlacklistRequestItemWire): BlacklistRequestItem {
  return {
    request_id: wire.request_id,
    call_id: wire.call_id,
    customer_ref: wire.customer_ref,
    display_hint: wire.display_hint,
    requested_by: wire.requested_by,
    reason: wire.reason,
    context_excerpt: wire.context_excerpt,
    evidence: toEvidence(wire.evidence),
    status: wire.status as BlacklistRequestItem["status"],
    requested_at: wire.requested_at,
    decided_by: wire.decided_by,
    decided_at: wire.decided_at,
    evidence_snapshot_at: wire.evidence_snapshot_at,
  };
}

function toEntryItem(wire: BlacklistEntryItemWire): BlacklistEntryItem {
  return {
    entry_id: wire.entry_id,
    customer_ref: wire.customer_ref,
    request_id: wire.request_id,
    approved_at: wire.approved_at,
    expires_at: wire.expires_at,
    released_at: wire.released_at,
    released_by: wire.released_by,
    release_reason: wire.release_reason,
    note: wire.note,
  };
}

// ── GET /hub/blacklist-requests ──────────────────────────────────────────

export async function fetchBlacklistRequests(
  accessToken: string,
  statusFilter?: string,
): Promise<BlacklistRequestItem[]> {
  const query = statusFilter !== undefined ? `?status=${encodeURIComponent(statusFilter)}` : "";
  const wire = await authedGet<{ requests: BlacklistRequestItemWire[] }>(
    `/hub/blacklist-requests${query}`,
    accessToken,
  );
  return wire.requests.map(toRequestItem);
}

// ── POST /hub/blacklist-requests/{request_id}/decision ──────────────────

export async function decideBlacklistRequestApi(
  accessToken: string,
  requestId: string,
  approve: boolean,
  expiresInDays?: number,
  note?: string,
): Promise<BlacklistRequestItem> {
  const wire = await authedPost<{ request: BlacklistRequestItemWire }>(
    `/hub/blacklist-requests/${encodeURIComponent(requestId)}/decision`,
    accessToken,
    { approve, expires_in_days: expiresInDays ?? null, note: note ?? null },
  );
  return toRequestItem(wire.request);
}

// ── GET /hub/blacklist-entries ────────────────────────────────────────────

export async function fetchBlacklistEntries(
  accessToken: string,
  activeOnly?: boolean,
): Promise<BlacklistEntryItem[]> {
  const query = activeOnly === true ? "?active_only=true" : "";
  const wire = await authedGet<{ entries: BlacklistEntryItemWire[] }>(
    `/hub/blacklist-entries${query}`,
    accessToken,
  );
  return wire.entries.map(toEntryItem);
}

// ── POST /hub/blacklist-entries/{entry_id}/release ───────────────────────

export async function releaseBlacklistEntryApi(
  accessToken: string,
  entryId: string,
  reason: string,
): Promise<BlacklistEntryItem> {
  const wire = await authedPost<{ entry: BlacklistEntryItemWire }>(
    `/hub/blacklist-entries/${encodeURIComponent(entryId)}/release`,
    accessToken,
    { reason },
  );
  return toEntryItem(wire.entry);
}

// ── GET /hub/calls (인증 불필요 — 총 건수만 쓴다) ───────────────────────────

/** 현황판 "완료 통화 누적". `call_list_router`에는 `require_admin`이 없다. */
export async function fetchCallListTotal(): Promise<number> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/hub/calls?limit=1`, {
      headers: { "ngrok-skip-browser-warning": "1" },
    });
  } catch (error) {
    throw new HubApiError(
      error instanceof Error ? `서버에 연결하지 못했다: ${error.message}` : "서버에 연결하지 못했다.",
      null,
    );
  }
  if (!response.ok) {
    throw new HubApiError(`요청이 실패했다 (${response.status})`, response.status);
  }
  const body = (await response.json()) as { total: string };
  return toNum(body.total);
}

// ── GET /hub/call-guard-flags ─────────────────────────────────────────────

/** 현황판 "콜가드 경고 누적" 하나만 쓴다 — 개별 항목 화면은 아직 없다. */
export async function fetchCallGuardFlagTotal(accessToken: string): Promise<number> {
  const wire = await authedGet<{ total: string }>("/hub/call-guard-flags?limit=1", accessToken);
  return toNum(wire.total);
}

// ── GET /hub/knowledge-gaps ───────────────────────────────────────────────

export interface KnowledgeGapItem {
  gap_id: string;
  module: "B" | "C" | "F";
  description: string;
  status: "open" | "resolved";
  created_at: string;
  call_id: string | null;
  domain: string | null;
}

interface KnowledgeGapItemWire {
  gap_id: string;
  module: "B" | "C" | "F";
  description: string;
  status: "open" | "resolved";
  created_at: string;
  call_id: string | null;
  segment_id: string | null;
  closure_id: string | null;
  domain: string | null;
}

/**
 * ⚠ **`KnowledgeGapTab.tsx`가 아직 이 모양을 소비하지 않는다.** 화면은 지금
 * `{call_id, query, found}`(상담원이 직접 검색해 못 찾은 질의) 기준으로 묶어 세는데,
 * 실제 계약은 `{module: B|C|F, description, status}`(더 넓은 D-4 공백)라 필드가
 * 대응되지 않는다 — 단순 이름 바꾸기로 못 옮긴다. 탭을 다시 설계하기 전까지는
 * 이 함수만 두고 화면에 연결하지 않는다.
 */
export async function fetchKnowledgeGaps(
  accessToken: string,
  options?: { module?: "B" | "C" | "F"; status?: "open" | "resolved" },
): Promise<KnowledgeGapItem[]> {
  const params = new URLSearchParams();
  if (options?.module !== undefined) {
    params.set("module", options.module);
  }
  if (options?.status !== undefined) {
    params.set("status", options.status);
  }
  const query = params.toString();
  const wire = await authedGet<{ gaps: KnowledgeGapItemWire[] }>(
    `/hub/knowledge-gaps${query.length > 0 ? `?${query}` : ""}`,
    accessToken,
  );
  return wire.gaps.map((g) => ({
    gap_id: g.gap_id,
    module: g.module,
    description: g.description,
    status: g.status,
    created_at: g.created_at,
    call_id: g.call_id,
    domain: g.domain,
  }));
}
