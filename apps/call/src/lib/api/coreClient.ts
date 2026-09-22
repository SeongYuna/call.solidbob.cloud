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

function get<T>(path: string, headers?: Record<string, string>): Promise<T> {
  return request<T>(path, { method: "GET", headers });
}

function post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body), headers });
}

// ── GET /hub/agents/me ────────────────────────────────────────────────────

interface AgentMeResponseWire {
  agent_id: string;
  display_name: string;
}

/**
 * 로그인 화면이 입력받은 토큰을 검증하는 자리(`decisions/307`). 판정(유효·폐기)은
 * 서버가 401로 이미 내리므로 여기서는 되묻지 않고 `CoreApiError`를 그대로 던진다.
 * `display_name`은 대기화면 인사말에 쓴다 — `agent_id`를 이름 대신 보여주지 않는다.
 */
export async function fetchAgentMe(token: string): Promise<{ agentId: string; displayName: string }> {
  const wire = await get<AgentMeResponseWire>("/hub/agents/me", { Authorization: `Bearer ${token}` });
  return { agentId: wire.agent_id, displayName: wire.display_name };
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
  /** `decisions/316` — null 은 미측정. `_types.StrField`의 "전부 문자열" 규칙에서도 null 은 예외다. */
  temperature_outliers: string | null;
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
    temperature_outliers:
      wire.temperature_outliers === null ? null : toNum(wire.temperature_outliers),
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
 * 상담원 토큰이 필요하다(`decisions/315` — `require_agent`, 신원은 저장하지 않고 확인만 한다).
 * `closeCall`과 같은 패턴: 토큰이 없으면 서버를 부르지 않고 바로 던진다.
 */
export async function submitCardFeedback(
  cardId: string,
  action: "adopted" | "ignored",
): Promise<{ feedbackId: string; cardId: string; action: "adopted" | "ignored" }> {
  const token = readAgentToken();
  if (token === null) {
    throw new CoreApiError(
      "상담원 토큰이 없다 — 관리자가 보낸 링크(?agent_token=...)로 다시 접속해야 한다.",
      null,
    );
  }
  const wire = await post<{ feedback_id: string; card_id: string; action: "adopted" | "ignored" }>(
    `/hub/cards/${cardId}/feedback`,
    { action },
    { Authorization: `Bearer ${token}` },
  );
  return { feedbackId: wire.feedback_id, cardId: wire.card_id, action: wire.action };
}

// ── POST /hub/calls/{call_id}/close ──────────────────────────────────────

export interface ClosureSegmentInput {
  segmentId: string;
  speaker: "customer" | "agent";
  text: string;
  isFinal: boolean;
  utteranceEndMs: number | null;
}

interface FollowUpActionWire {
  action_text: string;
}

interface CallSummaryResponseWire {
  call_id: string;
  summary_text: string;
  inquiry_type: string | null;
  follow_up_actions: FollowUpActionWire[];
  confirmed: string;
}

export interface CallSummaryDraft {
  callId: string;
  summaryText: string;
  inquiryType: string | null;
  followUpActions: string[];
  confirmed: boolean;
}

/**
 * `decisions/306` — 통화가 끝난 뒤 규칙 기반 초안을 만든다(생성 모델 아님, 유형은 늘 null).
 * ⚠ SEC-1 — `segments`에는 마스킹된 자막만 싣는다(원문 필드가 서버 스키마에 아예 없다).
 * 상담원 토큰을 싣는다 — 서버는 아직 이 헤더를 검증하지 않지만 `confirmSummary`·
 * `reviseSummary`와 같은 방식으로 맞춰 둔다. 토큰이 없으면 서버를 부르지 않고 바로 던진다.
 */
export async function closeCall(
  callId: string,
  segments: ClosureSegmentInput[],
): Promise<CallSummaryDraft> {
  const token = readAgentToken();
  if (token === null) {
    throw new CoreApiError(
      "상담원 토큰이 없다 — 관리자가 보낸 링크(?agent_token=...)로 다시 접속해야 한다.",
      null,
    );
  }
  const wire = await post<CallSummaryResponseWire>(
    `/hub/calls/${encodeURIComponent(callId)}/close`,
    {
      call_id: callId,
      segments: segments.map((s) => ({
        segment_id: Number(s.segmentId),
        speaker: s.speaker,
        text: s.text,
        is_final: s.isFinal,
        utterance_end_ms: s.utteranceEndMs,
      })),
    },
    { Authorization: `Bearer ${token}` },
  );
  return {
    callId: wire.call_id,
    summaryText: wire.summary_text,
    inquiryType: wire.inquiry_type,
    followUpActions: wire.follow_up_actions.map((a) => a.action_text),
    confirmed: toBool(wire.confirmed),
  };
}

// ── POST /hub/calls/{call_id}/summary-confirmation ───────────────────────

interface SummaryConfirmedResponseWire {
  call_id: string;
  summary_text: string;
  inquiry_type: string | null;
  follow_up_actions: string[];
  confirmed: string;
  confirmed_at: string;
}

export interface SummaryConfirmed extends CallSummaryDraft {
  confirmedAt: string;
}

/**
 * 상담원 토큰이 필요하다(`decisions/307`) — 확정은 사람이 했다는 표시라 익명으로 안 받는다.
 * 이미 확정된 통화는 409, 없는 통화는 404 — 여기서는 메시지 그대로 올려보낸다.
 */
export async function confirmSummary(
  callId: string,
  input: { summaryText: string; inquiryType: string | null; followUpActions: string[] },
): Promise<SummaryConfirmed> {
  const token = readAgentToken();
  if (token === null) {
    throw new CoreApiError(
      "상담원 토큰이 없다 — 관리자가 보낸 링크(?agent_token=...)로 다시 접속해야 한다.",
      null,
    );
  }
  const wire = await post<SummaryConfirmedResponseWire>(
    `/hub/calls/${encodeURIComponent(callId)}/summary-confirmation`,
    {
      summary_text: input.summaryText,
      inquiry_type: input.inquiryType,
      follow_up_actions: input.followUpActions,
    },
    { Authorization: `Bearer ${token}` },
  );
  return {
    callId: wire.call_id,
    summaryText: wire.summary_text,
    inquiryType: wire.inquiry_type,
    followUpActions: wire.follow_up_actions,
    confirmed: toBool(wire.confirmed),
    confirmedAt: wire.confirmed_at,
  };
}

// ── POST /hub/calls/{call_id}/summary-revision ───────────────────────────

interface SummaryRevisedResponseWire {
  call_id: string;
  summary_text: string;
  inquiry_type: string | null;
  follow_up_actions: string[];
  revision: { revision_id: string; revised_at: string };
}

export interface SummaryRevised {
  callId: string;
  summaryText: string;
  inquiryType: string | null;
  followUpActions: string[];
  revisedAt: string;
}

/**
 * 확정된 요약을 사유와 함께 고친다(`decisions/311`). 확정 전이면 409 — 상담원 토큰 필요.
 * 고치기 전 값은 서버가 이력으로 남긴다. 누가 고쳤는지는 저장하지 않는다.
 */
export async function reviseSummary(
  callId: string,
  input: { summaryText: string; reason: string; inquiryType: string | null; followUpActions: string[] },
): Promise<SummaryRevised> {
  const token = readAgentToken();
  if (token === null) {
    throw new CoreApiError(
      "상담원 토큰이 없다 — 관리자가 보낸 링크(?agent_token=...)로 다시 접속해야 한다.",
      null,
    );
  }
  const wire = await post<SummaryRevisedResponseWire>(
    `/hub/calls/${encodeURIComponent(callId)}/summary-revision`,
    {
      summary_text: input.summaryText,
      reason: input.reason,
      inquiry_type: input.inquiryType,
      follow_up_actions: input.followUpActions,
    },
    { Authorization: `Bearer ${token}` },
  );
  return {
    callId: wire.call_id,
    summaryText: wire.summary_text,
    inquiryType: wire.inquiry_type,
    followUpActions: wire.follow_up_actions,
    revisedAt: wire.revision.revised_at,
  };
}

// ── GET /hub/calls/{call_id}/record ──────────────────────────────────────

interface SavedCardWire {
  card_id: string;
  rank: string;
  title: string;
  summary: string;
  source_doc_id: string | null;
  similarity_score: string | null;
}

interface SavedRecommendationWire {
  recommendation_id: string;
  trigger_at_ms: string;
  internal_latency_ms: string | null;
  created_at: string;
  cards: SavedCardWire[];
}

interface SavedClosureItemWire {
  rank: string;
  document_name: string;
  informed: string;
}

interface SavedClosureWire {
  closure_id: string;
  procedure: string;
  verdict: string;
  detected: string;
  reason: string | null;
  source_doc_id: string | null;
  decided_at: string;
  items: SavedClosureItemWire[];
}

interface CallRecordResponseWire {
  call_id: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  summary_text: string | null;
  inquiry_type: string | null;
  summary_confirmed: string;
  follow_up_actions: { action_text: string; status: string }[];
  recommendations: SavedRecommendationWire[];
  closures: SavedClosureWire[];
}

export interface SavedCard {
  cardId: string;
  rank: number;
  title: string;
  summary: string;
  sourceDocId: string | null;
  similarityScore: number | null;
}

export interface SavedRecommendation {
  recommendationId: string;
  triggerAtMs: number;
  createdAt: string;
  cards: SavedCard[];
}

export interface SavedClosureItem {
  rank: number;
  documentName: string;
  informed: boolean;
}

export interface SavedClosure {
  closureId: string;
  procedure: string;
  verdict: "complete" | "incomplete";
  detected: boolean;
  reason: string | null;
  sourceDocId: string | null;
  decidedAt: string;
  items: SavedClosureItem[];
}

export interface CallRecord {
  callId: string;
  status: string;
  startedAt: string;
  endedAt: string | null;
  summaryText: string | null;
  inquiryType: string | null;
  summaryConfirmed: boolean;
  followUpActions: { text: string; status: string }[];
  recommendations: SavedRecommendation[];
  closures: SavedClosure[];
}

/**
 * `decisions/310`~`313` — 상담기록 재생 화면 전용. 전사는 싣지 않는다
 * (`fetchCallTranscript`가 따로 준다). 감정분석·통번역은 저장되지 않아 없다.
 */
export async function fetchCallRecord(callId: string): Promise<CallRecord> {
  const wire = await get<CallRecordResponseWire>(`/hub/calls/${encodeURIComponent(callId)}/record`);
  return {
    callId: wire.call_id,
    status: wire.status,
    startedAt: wire.started_at,
    endedAt: wire.ended_at,
    summaryText: wire.summary_text,
    inquiryType: wire.inquiry_type,
    summaryConfirmed: toBool(wire.summary_confirmed),
    followUpActions: wire.follow_up_actions.map((f) => ({ text: f.action_text, status: f.status })),
    recommendations: wire.recommendations.map((rec) => ({
      recommendationId: rec.recommendation_id,
      triggerAtMs: toNum(rec.trigger_at_ms),
      createdAt: rec.created_at,
      cards: rec.cards.map((c) => ({
        cardId: c.card_id,
        rank: toNum(c.rank),
        title: c.title,
        summary: c.summary,
        sourceDocId: c.source_doc_id,
        similarityScore: c.similarity_score === null ? null : toNum(c.similarity_score),
      })),
    })),
    closures: wire.closures.map((cl) => ({
      closureId: cl.closure_id,
      procedure: cl.procedure,
      verdict: cl.verdict as "complete" | "incomplete",
      detected: toBool(cl.detected),
      reason: cl.reason,
      sourceDocId: cl.source_doc_id,
      decidedAt: cl.decided_at,
      items: cl.items.map((i) => ({
        rank: toNum(i.rank),
        documentName: i.document_name,
        informed: toBool(i.informed),
      })),
    })),
  };
}

/**
 * GET /hub/calls 목록 API 연결 전 임시 mock. `isCoreApiConfigured()`가 false일 때
 * (또는 상담기록 "예시 재생" 화면에서) 화면이 이걸 그대로 쓴다 — 실제 API에는
 * 카드·종결·감정분석 재생 데이터가 없어 시나리오 재생 자체를 대체하지 않는다.
 */
export { listCallHistory, getCallTranscript, getHistoryPlayback } from "../../mock/callHistory";
