/**
 * `server`(FastAPI) `/hub/*` REST 호출. 티켓 `w4-dashboard-live-contract`.
 *
 * `VITE_CORE_API_URL`이 비어 있으면 이 클라이언트를 아예 부르지 않는다 —
 * 화면은 `mock/callHistory.ts`(상담기록 시나리오 재생)를 그대로 쓴다. 값이 있으면
 * 여기 함수들이 실제 REST 호출을 한다. ngrok으로 열었을 때 경고 페이지가 JSON
 * 대신 오는 것을 막으려고 `ngrok-skip-browser-warning`을 항상 붙인다.
 *
 * ⚠ 값은 전부 문자열로 온다(`_types.StrField`, 7.3절 계약 전체에 적용) — 여기서
 * number/boolean으로 되돌린다. 서버가 타입을 어기면(문자열이 아니면) 그 사실을
 * 감추지 않고 던진다.
 */
import { readAgentToken } from "../agentToken";
import type {
  BlacklistEvidence,
  BlacklistRequestItem,
  CallHistoryItem,
  RecommendationCard,
  TranscriptPage,
} from "../../types/contract";

export function coreApiUrl(): string {
  return (import.meta.env.VITE_CORE_API_URL ?? "").trim();
}

export function isCoreApiConfigured(): boolean {
  return coreApiUrl().length > 0;
}

export class CoreApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
  ) {
    super(message);
    this.name = "CoreApiError";
  }
}

function toBool(value: unknown): boolean {
  if (value === "true" || value === true) {
    return true;
  }
  if (value === "false" || value === false || value === undefined || value === null) {
    return false;
  }
  throw new CoreApiError(`불리언 필드에 예상 밖 값이 왔다: ${JSON.stringify(value)}`, null);
}

function toNum(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    throw new CoreApiError(`숫자 필드에 예상 밖 값이 왔다: ${JSON.stringify(value)}`, null);
  }
  return n;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = coreApiUrl();
  if (base.length === 0) {
    throw new CoreApiError("VITE_CORE_API_URL이 설정되지 않았다.", null);
  }
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "1",
        ...init?.headers,
      },
    });
  } catch (error) {
    throw new CoreApiError(
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
    throw new CoreApiError(message, response.status);
  }
  return (await response.json()) as T;
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

function post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body), headers });
}

// ── GET /hub/calls ────────────────────────────────────────────────────────

interface CallListItemWire {
  call_id: string;
  domain: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  stt_engine: string;
  channel_count: string;
  customer_id: string | null;
  inquiry_type: string | null;
  summary_confirmed: string;
}

interface CallListResponseWire {
  calls: CallListItemWire[];
  total: string;
  limit: string;
  offset: string;
}

export interface CallListPage {
  calls: CallHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * GET /hub/calls. ⚠ 서버는 아직 `customer_id`를 채우는 경로가 없어 늘 null이다
 * (F-3) — `CallHistoryItem.customer_ref`는 그때까지 빈 문자열로 온다.
 */
export async function fetchCallList(options?: {
  limit?: number;
  offset?: number;
}): Promise<CallListPage> {
  const params = new URLSearchParams();
  if (options?.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options?.offset !== undefined) {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  const wire = await get<CallListResponseWire>(`/hub/calls${query.length > 0 ? `?${query}` : ""}`);
  return {
    calls: wire.calls.map((c) => ({
      call_id: c.call_id,
      started_at: c.started_at,
      domain: c.domain as CallHistoryItem["domain"],
      inquiry_type: c.inquiry_type ?? "",
      customer_ref: c.customer_id ?? "",
    })),
    total: toNum(wire.total),
    limit: toNum(wire.limit),
    offset: toNum(wire.offset),
  };
}

// ── GET /hub/calls/{call_id}/transcript ──────────────────────────────────

interface MaskedSpanWire {
  type: string;
  span: [string, string];
}

interface TranscriptSegmentWire {
  segment_id: string;
  speaker: "customer" | "agent";
  text: string;
  masked: MaskedSpanWire[];
  is_final: string;
  utterance_end_ms: string | null;
}

interface TranscriptPageWire {
  call_id: string;
  segments: TranscriptSegmentWire[];
  total: string;
  limit: string;
  offset: string;
}

export async function fetchCallTranscript(
  callId: string,
  options?: { limit?: number; offset?: number },
): Promise<TranscriptPage> {
  const params = new URLSearchParams();
  if (options?.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options?.offset !== undefined) {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  const wire = await get<TranscriptPageWire>(
    `/hub/calls/${encodeURIComponent(callId)}/transcript${query.length > 0 ? `?${query}` : ""}`,
  );
  return {
    call_id: wire.call_id,
    segments: wire.segments.map((s) => ({
      segment_id: toNum(s.segment_id),
      speaker: s.speaker,
      text: s.text,
      masked: s.masked.map((m) => ({
        type: m.type as TranscriptPage["segments"][number]["masked"][number]["type"],
        span: [toNum(m.span[0]), toNum(m.span[1])] as [number, number],
      })),
      is_final: toBool(s.is_final),
      utterance_end_ms: s.utterance_end_ms === null ? null : toNum(s.utterance_end_ms),
    })),
    total: toNum(wire.total),
    limit: toNum(wire.limit),
    offset: toNum(wire.offset),
  };
}

// ── POST /hub/search ──────────────────────────────────────────────────────

interface RetrievedDocWire {
  doc_id: string;
  title: string;
  snippet: string;
  score: string;
}

interface SearchResponseWire {
  query: string;
  docs: RetrievedDocWire[];
}

/** B-6 수동 검색. 조항 목록 → 카드로 바꾸는 것은 이 함수(화면 몫)가 한다. */
export async function searchDocuments(utterance: string, topK?: number): Promise<RecommendationCard[]> {
  const wire = await post<SearchResponseWire>("/hub/search", {
    utterance,
    ...(topK !== undefined ? { top_k: topK } : {}),
  });
  return wire.docs.map((d) => ({
    title: d.title,
    summary: d.snippet,
    source: { doc_id: d.doc_id, title: d.title },
    similarity_score: toNum(d.score),
  }));
}

// ── POST /hub/blacklist-requests ─────────────────────────────────────────

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

interface BlacklistRequestCreatedResponseWire {
  request: BlacklistRequestItemWire;
  has_distress: string;
}

function toEvidence(wire: BlacklistEvidenceWire): BlacklistEvidence {
  return {
    call_duration_s: toNum(wire.call_duration_s),
    insult_count: toNum(wire.insult_count),
    threat_count: toNum(wire.threat_count),
    sexual_count: toNum(wire.sexual_count),
    // ⚠ 서버는 distress_count 를 저장·응답하지 않는다(`decisions/205` ④) — 화면
    // 전용 값이라 여기서는 채울 수 없다. `has_distress`(응답 최상위)로 대신 본다.
    distress_count: 0,
    temperature_outliers: toNum(wire.temperature_outliers),
  };
}

function toBlacklistRequestItem(wire: BlacklistRequestItemWire): BlacklistRequestItem {
  return {
    request_id: wire.request_id,
    call_id: wire.call_id,
    customer_ref: wire.customer_ref,
    display_hint: wire.display_hint ?? "",
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

/**
 * ⚠ 상담원 토큰이 필요하다(`decisions/307`) — 누가 요청했는지를 더 이상 본문
 * (`requested_by`)으로 안 받는다. 토큰은 `agentToken.ts`가 `?agent_token=` URL 쿼리로
 * 받아 sessionStorage에 둔 값을 그대로 쓴다. 토큰이 없으면 서버를 부르지 않고 바로 던진다.
 */
export async function createBlacklistRequest(input: {
  callId: string;
  reason: string;
}): Promise<{ request: BlacklistRequestItem; hasDistress: boolean }> {
  const token = readAgentToken();
  if (token === null) {
    throw new CoreApiError("상담원 토큰이 없다 — 관리자가 보낸 링크(?agent_token=...)로 다시 접속해야 한다.", null);
  }
  const wire = await post<BlacklistRequestCreatedResponseWire>(
    "/hub/blacklist-requests",
    { call_id: input.callId, reason: input.reason },
    { Authorization: `Bearer ${token}` },
  );
  return {
    request: toBlacklistRequestItem(wire.request),
    hasDistress: toBool(wire.has_distress),
  };
}

// ── POST /hub/cards/{card_id}/feedback ───────────────────────────────────

/**
 * ⚠ `card_id`는 `decisions/308`로 `RecommendResponse.cards[]`에 추가됐지만
 * 문자열이다(`card_feedback_schema.py` — 2026-09-15 정정, StrField). null일 수 있는
 * 카드(DB 미연결)는 호출하는 쪽에서 애초에 걸러야 한다. 아직 `TermsPanel`의
 * 「사용 표시」 토글에는 연결하지 않았다.
 */
export async function submitCardFeedback(
  cardId: string,
  action: "adopted" | "ignored",
): Promise<{ feedbackId: string; cardId: string; action: "adopted" | "ignored" }> {
  const wire = await post<{ feedback_id: string; card_id: string; action: "adopted" | "ignored" }>(
    `/hub/cards/${cardId}/feedback`,
    { action },
  );
  return { feedbackId: wire.feedback_id, cardId: wire.card_id, action: wire.action };
}

/**
 * GET /hub/calls 목록 API 연결 전 임시 mock. `isCoreApiConfigured()`가 false일 때
 * (또는 상담기록 "예시 재생" 화면에서) 화면이 이걸 그대로 쓴다 — 실제 API에는
 * 카드·종결·감정분석 재생 데이터가 없어 시나리오 재생 자체를 대체하지 않는다.
 */
export { listCallHistory, getCallTranscript, getHistoryPlayback } from "../../mock/callHistory";
