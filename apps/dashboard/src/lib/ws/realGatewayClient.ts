import type {
  ClosureEvent,
  ClosureType,
  ClosureVerdict,
  DemoDomain,
  DocumentSource,
  MaskedSpan,
  MaskType,
  RecommendationBatch,
  RecommendationCard,
  Speaker,
  TranscriptEvent,
} from "../../types/contract";
import type { GatewayClient, GatewayListener } from "./types";

type ParsedMessage =
  | { kind: "transcript"; payload: TranscriptEvent }
  | { kind: "recommendation"; payload: RecommendationBatch }
  | { kind: "closure"; payload: ClosureEvent };

export class RealGatewayClient implements GatewayClient {
  readonly mode = "live" as const;
  private socket: WebSocket | null = null;
  private listeners: GatewayListener | null = null;

  constructor(private readonly url: string) {}

  connect(listeners: GatewayListener): void {
    this.disconnect();
    this.listeners = listeners;
    listeners.onStatus({ mode: "live", connected: false });

    try {
      this.socket = new WebSocket(this.url);
    } catch {
      listeners.onError("게이트웨이에 연결하지 못했습니다.");
      return;
    }

    this.socket.addEventListener("open", () => {
      this.listeners?.onStatus({ mode: "live", connected: true });
    });

    this.socket.addEventListener("message", (event: MessageEvent<string>) => {
      this.handleMessage(event.data);
    });

    this.socket.addEventListener("error", () => {
      this.listeners?.onError("게이트웨이 연결에 문제가 생겼습니다.");
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
   * 수동 검색 메시지는 7.3절 계약에 아직 없다. 임의의 형식을 보내면 서버가
   * 모르는 메시지로 버리고 화면은 결과를 기다리게 되므로, 안 된다고 말한다.
   */
  manualSearch(): Promise<never> {
    return Promise.reject(
      new Error("수동 검색은 아직 게이트웨이에 연결되지 않았습니다."),
    );
  }

  /** §2.5 D 통화 후 처리도 계약이 없다. 지어내지 않고 없다고 말한다. */
  wrapUp(): Promise<never> {
    return Promise.reject(
      new Error("통화 후 처리는 아직 게이트웨이에 연결되지 않았습니다."),
    );
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
      listeners.onError("게이트웨이 메시지를 읽지 못했습니다.");
      return;
    }

    const message = parseGatewayMessage(parsed);
    if (message === null) {
      listeners.onError("알 수 없는 게이트웨이 메시지입니다.");
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
    listeners.onClosure(message.payload);
  }
}

export function parseGatewayMessage(value: unknown): ParsedMessage | null {
  const body = unwrapPayload(value);
  if (body === null) {
    return null;
  }

  const tagged = readString(body, "type");
  if (tagged === "transcript" || tagged === "recommendation" || tagged === "closure") {
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
  kind: "transcript" | "recommendation" | "closure",
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
  const payload = parseClosure(body);
  return payload === null ? null : { kind, payload };
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
  return card;
}

function parseClosure(body: Record<string, unknown>): ClosureEvent | null {
  const call_id = readString(body, "call_id");
  const closure_type = readClosureType(body.closure_type);
  const reason = readString(body, "reason");
  const verdict = readVerdict(body.verdict);
  const source = parseSource(body.source);
  const missing = parseStringList(body.missing);
  const evidence = parseEvidence(body.evidence);
  if (
    call_id === null ||
    closure_type === null ||
    reason === null ||
    verdict === null ||
    source === null ||
    missing === null ||
    evidence === null
  ) {
    return null;
  }
  const event: ClosureEvent = {
    call_id,
    closure_type,
    reason,
    evidence,
    verdict,
    missing,
    source,
  };
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

function readClosureType(value: unknown): ClosureType | string | null {
  const str = readStringValue(value);
  if (str === null || str.length === 0) {
    return null;
  }
  // 금융·쇼핑 ClosureType — 4도메인 시절 코드, decisions/201로 다산 단일화되며
  // 신규 시나리오에는 쓰지 않는다. 파서는 그대로 받는다.
  // 다산 RequiredDocsType 도 서비스명 문자열이라 검증 없이 그대로 통과시킨다.
  return str;
}

function readVerdict(value: unknown): ClosureVerdict | null {
  const str = readStringValue(value);
  if (str === "approved" || str === "blocked") {
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
