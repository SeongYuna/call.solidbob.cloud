import { closeCall, searchDocuments } from "../api/coreClient";
import type {
  CallGuardFlag,
  CallWrapUp,
  ClosureEvent,
  ClosureVerdict,
  ComplianceFinding,
  ComplianceUnavailable,
  DemoDomain,
  DocumentSource,
  ManualSearchRequest,
  MaskedSpan,
  MaskType,
  RecommendationBatch,
  RecommendationCard,
  Speaker,
  TranscriptEvent,
} from "../../types/contract";
import type { CallMediatorClient, CallMediatorListener, WrapUpSegment } from "./types";

type ParsedMessage =
  | { kind: "transcript"; payload: TranscriptEvent }
  | { kind: "recommendation"; payload: RecommendationBatch }
  | { kind: "recommendation_pending"; payload: { call_id: string } }
  | { kind: "call_guard"; payload: { segment_id: string; flags: CallGuardFlag[] } }
  | { kind: "compliance"; payload: { segment_id: string; findings: ComplianceFinding[] } }
  | { kind: "compliance_unavailable"; payload: { segment_id: string; event: ComplianceUnavailable } }
  | { kind: "closure"; payload: ClosureEvent };

export class RealCallMediatorClient implements CallMediatorClient {
  readonly mode = "live" as const;
  private socket: WebSocket | null = null;
  private listeners: CallMediatorListener | null = null;

  constructor(private readonly url: string) {}

  connect(listeners: CallMediatorListener): void {
    this.disconnect();
    this.listeners = listeners;
    listeners.onStatus({ mode: "live", connected: false });

    try {
      this.socket = new WebSocket(this.url);
    } catch {
      listeners.onError("콜 미디에이터에 연결하지 못했습니다.");
      return;
    }

    this.socket.addEventListener("open", () => {
      this.listeners?.onStatus({ mode: "live", connected: true });
    });

    this.socket.addEventListener("message", (event: MessageEvent<string>) => {
      this.handleMessage(event.data);
    });

    this.socket.addEventListener("error", () => {
      this.listeners?.onError("콜 미디에이터 연결에 문제가 생겼습니다.");
    });

    this.socket.addEventListener("close", () => {
      this.listeners?.onStatus({ mode: "live", connected: false });
    });
  }

  disconnect(): void {
    if (this.socket !== null) {
      this.socket.close();
      this.socket = null;
    }
    this.listeners = null;
  }

  /**
   * B-6 수동 검색 — `POST /hub/search`(REST). 웹소켓 계약이 아니라 별도 REST
   * 호출이라 콜 미디에이터 연결 여부와 무관하게 바로 부른다(`w4-dashboard-live-contract`).
   * `call_id`는 검색 자체에는 쓰이지 않는다(서버 계약에 없음) — 결과를 그
   * 통화에 붙이는 것은 호출부(스토어) 몫이다.
   */
  async manualSearch(request: ManualSearchRequest): Promise<RecommendationBatch> {
    const cards = await searchDocuments(request.query);
    return {
      fired: true,
      call_id: request.call_id,
      trigger_at_ms: 0,
      cards,
      internal_latency_ms: 0,
    };
  }

  /**
   * `decisions/306` — `POST /hub/calls/{id}/close`. D-2 분류는 규칙 기반이라 유형이
   * 늘 `null`로 온다 — 카테고리를 지어내지 않고 빈 채로 둔다(`callSummaryFromWrapUp`가
   * 빈 문자열이면 칩을 안 그린다). 감정분석·지역자원도 서버에 없어 비운다.
   */
  async wrapUp(callId: string, segments: WrapUpSegment[]): Promise<CallWrapUp> {
    if (segments.length === 0) {
      throw new Error("발화가 없어 통화 후 처리를 만들 수 없습니다.");
    }
    const draft = await closeCall(
      callId,
      segments.map((s) => ({
        segmentId: s.segment_id,
        speaker: s.speaker,
        text: s.text,
        isFinal: s.is_final,
        utteranceEndMs: s.utterance_end_ms,
      })),
    );
    return {
      call_id: draft.callId,
      summary: [draft.summaryText],
      category: draft.inquiryType ?? "",
      follow_ups: draft.followUpActions,
    };
  }

  private handleMessage(raw: string): void {
    const listeners = this.listeners;
    if (listeners === null) {
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw) as unknown;
    } catch {
      listeners.onError("콜 미디에이터 메시지를 읽지 못했습니다.");
      return;
    }

    const message = parseCallMediatorMessage(parsed);
    if (message === null) {
      listeners.onError("알 수 없는 콜 미디에이터 메시지입니다.");
      return;
    }

    if (message.kind === "transcript") {
      listeners.onTranscript(message.payload);
      return;
    }
    if (message.kind === "recommendation") {
      listeners.onRecommendation(message.payload);
      return;
    }
    if (message.kind === "recommendation_pending") {
      listeners.onRecommendationPending?.(message.payload.call_id);
      return;
    }
    if (message.kind === "call_guard") {
      for (const flag of message.payload.flags) {
        listeners.onCallGuard?.(message.payload.segment_id, flag);
      }
      return;
    }
    if (message.kind === "compliance") {
      for (const finding of message.payload.findings) {
        listeners.onCompliance?.(message.payload.segment_id, finding);
      }
      return;
    }
    if (message.kind === "compliance_unavailable") {
      listeners.onComplianceUnavailable?.(message.payload.segment_id, message.payload.event);
      return;
    }
    listeners.onClosure(message.payload);
  }
}

export function parseCallMediatorMessage(value: unknown): ParsedMessage | null {
  const body = unwrapPayload(value);
  if (body === null) {
    return null;
  }

  const tagged = readString(body, "type");
  if (
    tagged === "transcript" ||
    tagged === "recommendation" ||
    tagged === "recommendation_pending" ||
    tagged === "call_guard" ||
    tagged === "compliance" ||
    tagged === "compliance_unavailable" ||
    tagged === "closure"
  ) {
    const inner = isRecord(body.payload) ? body.payload : body;
    return parseByKind(tagged, inner);
  }

  if (hasKeys(body, ["segment_id", "speaker", "text"])) {
    return parseByKind("transcript", body);
  }
  // fired:false 응답에는 cards·trigger_at_ms 가 없다 (server/apps/hub 참고) — fired 단독으로도 잡는다.
  if (hasKeys(body, ["cards", "trigger_at_ms"]) || hasKeys(body, ["fired"])) {
    return parseByKind("recommendation", body);
  }
  if (hasKeys(body, ["verdict", "evidence", "missing"])) {
    return parseByKind("closure", body);
  }
  return null;
}

function parseByKind(
  kind:
    | "transcript"
    | "recommendation"
    | "recommendation_pending"
    | "call_guard"
    | "compliance"
    | "compliance_unavailable"
    | "closure",
  body: Record<string, unknown>,
): ParsedMessage | null {
  if (kind === "transcript") {
    const payload = parseTranscript(body);
    return payload === null ? null : { kind, payload };
  }
  if (kind === "recommendation") {
    const payload = parseRecommendation(body);
    return payload === null ? null : { kind, payload };
  }
  if (kind === "recommendation_pending") {
    const payload = parseRecommendationPending(body);
    return payload === null ? null : { kind, payload };
  }
  if (kind === "call_guard") {
    const payload = parseCallGuard(body);
    return payload === null ? null : { kind, payload };
  }
  if (kind === "compliance") {
    const payload = parseCompliance(body);
    return payload === null ? null : { kind, payload };
  }
  if (kind === "compliance_unavailable") {
    const payload = parseComplianceUnavailable(body);
    return payload === null ? null : { kind, payload };
  }
  const payload = parseClosure(body);
  return payload === null ? null : { kind, payload };
}

/** `services/call-mediator`의 `RecommendationPending` — 「검색 중」 신호. 값은 문자열(7.3절). */
function parseRecommendationPending(body: Record<string, unknown>): { call_id: string } | null {
  const call_id = readString(body, "call_id");
  return call_id === null ? null : { call_id };
}

/** `CallGuardCheckResponse` 그대로 — 한 세그먼트에 잡힌 갈래 여러 건. */
function parseCallGuard(
  body: Record<string, unknown>,
): { segment_id: string; flags: CallGuardFlag[] } | null {
  const segment_id = readString(body, "segment_id");
  if (segment_id === null || !Array.isArray(body.flags)) {
    return null;
  }
  const segmentIdNum = Number(segment_id);
  const flags: CallGuardFlag[] = [];
  for (const item of body.flags) {
    if (!isRecord(item)) {
      return null;
    }
    const category = readCallGuardCategory(item.category);
    if (category === null) {
      return null;
    }
    flags.push({ segment_id: segmentIdNum, category });
  }
  return { segment_id, flags };
}

function readCallGuardCategory(value: unknown): CallGuardFlag["category"] | null {
  const str = readStringValue(value);
  if (str === "insult" || str === "threat" || str === "sexual" || str === "distress") {
    return str;
  }
  return null;
}

/**
 * `ComplianceCheckResponse` 그대로(`compliance_schema.py` `ComplianceFindingSchema`) —
 * 한 세그먼트에 잡힌 위반 여러 건. `alternative_source`는 선택 필드라 `parseClosure`의
 * `source`와 같은 방식으로 있을 때만 검증한다.
 */
function parseCompliance(
  body: Record<string, unknown>,
): { segment_id: string; findings: ComplianceFinding[] } | null {
  const segment_id = readString(body, "segment_id");
  if (segment_id === null || !Array.isArray(body.findings)) {
    return null;
  }
  const segmentIdNum = Number(segment_id);
  const findings: ComplianceFinding[] = [];
  for (const item of body.findings) {
    if (!isRecord(item)) {
      return null;
    }
    const rule_code = readString(item, "rule_code");
    const phrase = readString(item, "phrase");
    if (rule_code === null || phrase === null) {
      return null;
    }
    const finding: ComplianceFinding = { segment_id: segmentIdNum, rule_code, phrase };
    if (item.alternative_source !== undefined && item.alternative_source !== null) {
      const source = parseSource(item.alternative_source);
      if (source === null) {
        return null;
      }
      finding.alternative_source = source;
    }
    findings.push(finding);
  }
  return { segment_id, findings };
}

/**
 * `ComplianceUnavailable` 그대로(`services/call-mediator/src/app/ports.ts`) — 검사가
 * 실패했다는 신호다. `status`는 고정 값 집합이 아니라 자유 문자열이라(`statusOf()`)
 * enum 검증 없이 `readString`으로만 받는다.
 */
function parseComplianceUnavailable(
  body: Record<string, unknown>,
): { segment_id: string; event: ComplianceUnavailable } | null {
  const call_id = readString(body, "call_id");
  const segment_id = readString(body, "segment_id");
  const status = readString(body, "status");
  if (call_id === null || segment_id === null || status === null) {
    return null;
  }
  return { segment_id, event: { call_id, segment_id: Number(segment_id), status } };
}

function unwrapPayload(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  return value;
}

function parseTranscript(body: Record<string, unknown>): TranscriptEvent | null {
  const call_id = readString(body, "call_id");
  const segment_id = readString(body, "segment_id");
  const speaker = readSpeaker(body.speaker);
  const text = readString(body, "text");
  const is_final = readBoolean(body, "is_final");
  const utterance_end_ms = readNumber(body, "utterance_end_ms");
  const masked = parseMaskedList(body.masked);
  if (
    call_id === null ||
    segment_id === null ||
    speaker === null ||
    text === null ||
    is_final === null ||
    utterance_end_ms === null ||
    masked === null
  ) {
    return null;
  }
  const event: TranscriptEvent = {
    call_id,
    segment_id,
    speaker,
    text,
    masked,
    is_final,
    utterance_end_ms,
  };
  const domain = readDomain(body.domain);
  if (domain !== undefined) {
    event.domain = domain;
  }
  return event;
}

function parseRecommendation(body: Record<string, unknown>): RecommendationBatch | null {
  const fired = readBoolean(body, "fired");
  if (fired === null) {
    return null;
  }

  if (!fired) {
    // 트리거 미발동 — 검색조차 하지 않았다. 서버는 call_id·cards 등을 보내지 않는다.
    const batch: RecommendationBatch = {
      fired: false,
      call_id: readString(body, "call_id") ?? "",
      trigger_at_ms: readNumber(body, "trigger_at_ms") ?? 0,
      cards: [],
      internal_latency_ms: readNumber(body, "internal_latency_ms") ?? 0,
    };
    const domain = readDomain(body.domain);
    if (domain !== undefined) {
      batch.domain = domain;
    }
    return batch;
  }

  const call_id = readString(body, "call_id");
  const trigger_at_ms = readNumber(body, "trigger_at_ms");
  const internal_latency_ms = readNumber(body, "internal_latency_ms");
  if (
    call_id === null ||
    trigger_at_ms === null ||
    internal_latency_ms === null ||
    !Array.isArray(body.cards)
  ) {
    return null;
  }
  const cards: RecommendationCard[] = [];
  for (const item of body.cards) {
    if (!isRecord(item)) {
      return null;
    }
    const card = parseCard(item);
    if (card === null) {
      return null;
    }
    cards.push(card);
  }
  const batch: RecommendationBatch = {
    fired: true,
    call_id,
    trigger_at_ms,
    cards,
    internal_latency_ms,
  };
  const domain = readDomain(body.domain);
  if (domain !== undefined) {
    batch.domain = domain;
  }
  return batch;
}

function parseCard(body: Record<string, unknown>): RecommendationCard | null {
  const title = readString(body, "title");
  const summary = readString(body, "summary");
  // NOTE: 서버가 아직 decisions/003(similarity_score) 대신 score로
  // 응답하고 있어 임시 방어 처리. 장민석님이 서버 고치면 이 fallback은
  // 제거 가능.
  const similarity_score =
    readNumber(body, "similarity_score") ?? readNumber(body, "score");
  const source = parseSource(body.source);
  if (title === null || summary === null || similarity_score === null || source === null) {
    return null;
  }
  const card: RecommendationCard = { title, summary, source, similarity_score };
  // 계약에 없는 필드라 없어도 통과시킨다 — 없으면 auto 로 본다.
  const sourceType = readStringValue(body.source_type);
  if (sourceType === "manual" || sourceType === "auto") {
    card.source_type = sourceType;
  }
  // `decisions/308` — DB 미연결 카드는 null 로 온다. 카드 피드백을 보낼 수 없다는 뜻이다.
  card.card_id = readStringValue(body.card_id);
  return card;
}

/**
 * `_project/decisions/305` — `closure_type`·`approved`/`blocked`를 걷어내고
 * `procedure`·`verdict: complete/incomplete`·`detected`로 바꿨다. `reason`·`source`·
 * `conditional`은 서버 DTO에서도 선택 필드다(`closure_verdict_dto.py`).
 */
function parseClosure(body: Record<string, unknown>): ClosureEvent | null {
  const call_id = readString(body, "call_id");
  const procedure = readString(body, "procedure");
  const verdict = readVerdict(body.verdict);
  const missing = parseStringList(body.missing);
  const evidence = parseEvidence(body.evidence);
  const detected = readBoolean(body, "detected");
  if (
    call_id === null ||
    procedure === null ||
    verdict === null ||
    missing === null ||
    evidence === null ||
    detected === null
  ) {
    return null;
  }
  const event: ClosureEvent = {
    call_id,
    procedure,
    evidence,
    verdict,
    missing,
    detected,
  };
  const procedureTitle = readStringValue(body.procedure_title);
  if (procedureTitle !== null) {
    event.procedure_title = procedureTitle;
  }
  const reason = readStringValue(body.reason);
  if (reason !== null) {
    event.reason = reason;
  }
  if (body.source !== undefined && body.source !== null) {
    const source = parseSource(body.source);
    if (source === null) {
      return null;
    }
    event.source = source;
  }
  if (body.conditional !== undefined && body.conditional !== null) {
    const conditional = parseStringList(body.conditional);
    if (conditional === null) {
      return null;
    }
    event.conditional = conditional;
  }
  const domain = readDomain(body.domain);
  if (domain !== undefined) {
    event.domain = domain;
  }
  if (readStringValue(body.is_example) === "true") {
    event.is_example = true;
  }
  return event;
}

function parseSource(value: unknown): DocumentSource | null {
  if (!isRecord(value)) {
    return null;
  }
  const doc_id = readString(value, "doc_id");
  const title = readString(value, "title");
  if (doc_id === null || title === null) {
    return null;
  }
  return { doc_id, title };
}

function parseMaskedList(value: unknown): MaskedSpan[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const spans: MaskedSpan[] = [];
  for (const item of value) {
    if (!isRecord(item)) {
      return null;
    }
    const type = readMaskType(item.type);
    const span = parseSpan(item.span);
    if (type === null || span === null) {
      return null;
    }
    spans.push({ type, span });
  }
  return spans;
}

function parseSpan(value: unknown): [number, number] | null {
  if (!Array.isArray(value) || value.length !== 2) {
    return null;
  }
  const start = readStringValue(value[0]);
  const end = readStringValue(value[1]);
  if (start === null || end === null) {
    return null;
  }
  const startNum = Number(start);
  const endNum = Number(end);
  if (!Number.isFinite(startNum) || !Number.isFinite(endNum)) {
    return null;
  }
  return [startNum, endNum];
}

function parseStringList(value: unknown): string[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const items: string[] = [];
  for (const item of value) {
    const str = readStringValue(item);
    if (str === null) {
      return null;
    }
    items.push(str);
  }
  return items;
}

function parseEvidence(value: unknown): Record<string, boolean> | null {
  if (!isRecord(value)) {
    return null;
  }
  const evidence: Record<string, boolean> = {};
  for (const [key, flag] of Object.entries(value)) {
    const raw = readStringValue(flag);
    if (raw === "true") {
      evidence[key] = true;
    } else if (raw === "false") {
      evidence[key] = false;
    } else {
      return null;
    }
  }
  return evidence;
}

function readSpeaker(value: unknown): Speaker | null {
  const str = readStringValue(value);
  if (str === "customer" || str === "agent") {
    return str;
  }
  return null;
}

function readVerdict(value: unknown): ClosureVerdict | null {
  const str = readStringValue(value);
  if (str === "complete" || str === "incomplete") {
    return str;
  }
  return null;
}

function readMaskType(value: unknown): MaskType | null {
  const str = readStringValue(value);
  if (
    str === "P1" ||
    str === "P2" ||
    str === "P3" ||
    str === "P4" ||
    str === "P5" ||
    str === "P6" ||
    str === "P7"
  ) {
    return str;
  }
  return null;
}

function readDomain(value: unknown): DemoDomain | undefined {
  const str = readStringValue(value);
  if (str === "dasan") {
    return str;
  }
  return undefined;
}

/**
 * 2026-09-10 — 백엔드가 모든 응답 필드를 문자열로 보내기로 했다(장민석 확인,
 * ngrok 실측). 그 밖의 타입이 오면 계약 위반이므로 조용히 넘기지 않고 즉시
 * 알린다. 실제 값(number·boolean)으로의 변환은 이 함수를 통과한 뒤 각
 * read*() 가 한다 — 나머지 앱 코드는 지금처럼 number·boolean 을 그대로 쓴다.
 */
function readStringValue(value: unknown): string | null {
  // undefined(필드 없음)·null(명시적 없음, 예: RecommendResponse.domain) 은
  // "타입이 틀렸다"가 아니라 "값이 없다"이므로 alert 대상이 아니다.
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value !== "string") {
    alert("데이터 타입이 틀립니다");
    return null;
  }
  return value;
}

function readString(body: Record<string, unknown>, key: string): string | null {
  return readStringValue(body[key]);
}

function readNumber(body: Record<string, unknown>, key: string): number | null {
  const raw = readStringValue(body[key]);
  if (raw === null) {
    return null;
  }
  const num = Number(raw);
  return Number.isFinite(num) ? num : null;
}

function readBoolean(body: Record<string, unknown>, key: string): boolean | null {
  const raw = readStringValue(body[key]);
  if (raw === "true") {
    return true;
  }
  if (raw === "false") {
    return false;
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasKeys(body: Record<string, unknown>, keys: readonly string[]): boolean {
  return keys.every((key) => key in body);
}
