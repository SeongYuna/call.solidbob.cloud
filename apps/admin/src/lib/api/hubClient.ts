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

function toBool(value: unknown): boolean {
  if (value === "true" || value === true) {
    return true;
  }
  if (value === "false" || value === false || value === undefined || value === null) {
    return false;
  }
  throw new HubApiError(`불리언 필드에 예상 밖 값이 왔다: ${JSON.stringify(value)}`, null);
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

function authedPut<T>(path: string, accessToken: string, body: unknown): Promise<T> {
  return authedRequest<T>(path, accessToken, { method: "PUT", body: JSON.stringify(body) });
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

// ── POST /hub/blacklist-entries/{entry_id}/expiry ─────────────────────────
// `decisions/309` — 만료 연장·단축 실제 API (`decisions/205`의 "연장은 새 요청으로만" 철회).
// ⚠ 서버는 `expires_in_days`를 1~365(MAX_EXPIRES_IN_DAYS)로 제한한다 — 화면 입력도 12개월(365일) 상한.

export interface ExpiryChangeItem {
  change_id: string;
  entry_id: string;
  previous_expires_at: string;
  new_expires_at: string;
  changed_by: string;
  reason: string;
  changed_at: string;
}

interface ExpiryChangeItemWire {
  change_id: string;
  entry_id: string;
  previous_expires_at: string;
  new_expires_at: string;
  changed_by: string;
  reason: string;
  changed_at: string;
}

function toExpiryChangeItem(wire: ExpiryChangeItemWire): ExpiryChangeItem {
  return { ...wire };
}

export async function changeBlacklistEntryExpiry(
  accessToken: string,
  entryId: string,
  expiresInDays: number,
  reason: string,
): Promise<{ entry: BlacklistEntryItem; change: ExpiryChangeItem }> {
  const wire = await authedPost<{ entry: BlacklistEntryItemWire; change: ExpiryChangeItemWire }>(
    `/hub/blacklist-entries/${encodeURIComponent(entryId)}/expiry`,
    accessToken,
    { expires_in_days: expiresInDays, reason },
  );
  return { entry: toEntryItem(wire.entry), change: toExpiryChangeItem(wire.change) };
}

// ── GET /hub/blacklist-entries/{entry_id}/expiry-changes ──────────────────

export async function fetchBlacklistExpiryChanges(
  accessToken: string,
  entryId: string,
): Promise<ExpiryChangeItem[]> {
  const wire = await authedGet<{ changes: ExpiryChangeItemWire[] }>(
    `/hub/blacklist-entries/${encodeURIComponent(entryId)}/expiry-changes`,
    accessToken,
  );
  return wire.changes.map(toExpiryChangeItem);
}

// ── /admin/agent-tokens — 상담원 토큰 발급·목록·폐기 (`decisions/307`) ──────

export interface AgentTokenItem {
  id: string;
  agent_id: string;
  issued_by: string | null;
  issued_at: string;
  revoked_at: string | null;
}

interface AgentTokenItemWire {
  id: string;
  agent_id: string;
  issued_by: string | null;
  issued_at: string;
  revoked_at: string | null;
}

function toAgentTokenItem(wire: AgentTokenItemWire): AgentTokenItem {
  return { ...wire };
}

/** 응답의 `token` 은 이번 한 번만 보인다 — 서버가 해시만 저장해 다시 못 보여준다. */
export async function issueAgentToken(
  accessToken: string,
  agentId: string,
): Promise<{ token: string; item: AgentTokenItem }> {
  const wire = await authedPost<{ token: string; item: AgentTokenItemWire }>(
    "/admin/agent-tokens",
    accessToken,
    { agent_id: agentId },
  );
  return { token: wire.token, item: toAgentTokenItem(wire.item) };
}

export async function fetchAgentTokens(accessToken: string, agentId?: string): Promise<AgentTokenItem[]> {
  const query = agentId !== undefined ? `?agent_id=${encodeURIComponent(agentId)}` : "";
  const wire = await authedGet<{ tokens: AgentTokenItemWire[] }>(`/admin/agent-tokens${query}`, accessToken);
  return wire.tokens.map(toAgentTokenItem);
}

export async function revokeAgentToken(accessToken: string, tokenId: string): Promise<AgentTokenItem> {
  const wire = await authedPost<AgentTokenItemWire>(
    `/admin/agent-tokens/${encodeURIComponent(tokenId)}/revoke`,
    accessToken,
    {},
  );
  return toAgentTokenItem(wire);
}

// ── /hub/routing-settings — J-5 베테랑 배정 기준 (`decisions/313`) ──────────

export interface RoutingSetting {
  veteranYears: number;
  /** false면 저장값이 없어 기본값(도메인이 갖는 `DEFAULT_VETERAN_YEARS`)이다. */
  saved: boolean;
  updatedAt: string | null;
  updatedBy: string | null;
}

interface RoutingSettingWire {
  veteran_years: string;
  saved: string;
  updated_at: string | null;
  updated_by: string | null;
}

function toRoutingSetting(wire: RoutingSettingWire): RoutingSetting {
  return {
    veteranYears: toNum(wire.veteran_years),
    saved: toBool(wire.saved),
    updatedAt: wire.updated_at,
    updatedBy: wire.updated_by,
  };
}

export async function fetchRoutingSetting(accessToken: string): Promise<RoutingSetting> {
  const wire = await authedGet<RoutingSettingWire>("/hub/routing-settings", accessToken);
  return toRoutingSetting(wire);
}

export async function saveRoutingSetting(accessToken: string, veteranYears: number): Promise<RoutingSetting> {
  const wire = await authedPut<RoutingSettingWire>("/hub/routing-settings", accessToken, {
    veteran_years: veteranYears,
  });
  return toRoutingSetting(wire);
}

// ── POST /hub/blacklist-retention/purge — 보존 정리 (`decisions/312`) ──────

export interface RetentionPurgeResult {
  retentionDays: number;
  cutoff: string;
  expiryChangeReasonsPurged: number;
  rejectedRequestsPurged: number;
}

interface RetentionPurgeResponseWire {
  retention_days: string;
  cutoff: string;
  expiry_change_reasons_purged: string;
  rejected_requests_purged: string;
}

/** 몇 번을 불러도 결과가 같다 — 확인 다이얼로그 이상의 되돌리기 방지 장치는 서버가 갖는다. */
export async function purgeBlacklistRetention(accessToken: string): Promise<RetentionPurgeResult> {
  const wire = await authedPost<RetentionPurgeResponseWire>("/hub/blacklist-retention/purge", accessToken, {});
  return {
    retentionDays: toNum(wire.retention_days),
    cutoff: wire.cutoff,
    expiryChangeReasonsPurged: toNum(wire.expiry_change_reasons_purged),
    rejectedRequestsPurged: toNum(wire.rejected_requests_purged),
  };
}
