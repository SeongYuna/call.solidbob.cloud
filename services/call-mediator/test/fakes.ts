// Requirement: QUA-1
/** 테스트용 가짜 포트 — 구글·서버 없이 파이프라인을 돌린다. */
import {
  HubError,
  type Broadcaster,
  type CallGuardCheckRequest,
  type CallGuardPayload,
  type ComplianceCheckRequest,
  type CompliancePayload,
  type ClosurePayload,
  type RequiredDocsCheckRequest,
  type CallStartRequest,
  type CallMediatorMessage,
  type HubPort,
  type LedgerStore,
  type Logger,
  type MaskedTranscript,
  type RawTranscript,
  type RecommendPayload,
  type RecommendRequest,
  type RoutingDecisionPayload,
  type RoutingDecisionRequest,
  type SttEngine,
  type SttHandlers,
  type SttOpenOptions,
  type SttStream,
} from "../src/app/ports.ts";

export function newLog(): Logger & { warnings: string[] } {
  const warnings: string[] = [];
  return { warnings, info: () => {}, warn: (message) => warnings.push(message) };
}

/** 채널별로 열린 가짜 STT 스트림. 테스트가 결과를 직접 흘린다. */
export class FakeSttStream implements SttStream {
  readonly handlers: SttHandlers;
  readonly sampleRate: number;
  readonly options: SttOpenOptions;
  bytes = 0;
  ended = false;

  constructor(sampleRate: number, handlers: SttHandlers, options: SttOpenOptions = {}) {
    this.sampleRate = sampleRate;
    this.handlers = handlers;
    this.options = options;
  }

  write(pcm: Buffer): void {
    this.bytes += pcm.byteLength;
  }

  end(): void {
    if (this.ended) {
      return;
    }
    this.ended = true;
    queueMicrotask(() => this.handlers.onEnd());
  }

  emit(text: string, isFinal: boolean, audioEndMs: number, speakerLabel?: string): void {
    this.handlers.onResult({ text, isFinal, audioEndMs, ...(speakerLabel === undefined ? {} : { speakerLabel }) });
  }
}

export class FakeStt implements SttEngine {
  readonly name = "fake-stt";
  unavailableReason: string | null = null;
  readonly streams: FakeSttStream[] = [];

  open(sampleRate: number, handlers: SttHandlers, options: SttOpenOptions = {}): SttStream {
    const stream = new FakeSttStream(sampleRate, handlers, options);
    this.streams.push(stream);
    return stream;
  }

  last(): FakeSttStream {
    const stream = this.streams[this.streams.length - 1];
    if (stream === undefined) {
      throw new Error("열린 STT 스트림이 없다");
    }
    return stream;
  }
}

/** 서버 흉내. 숫자를 `*` 로 가려 돌려준다 — 값은 계약대로 전부 문자열. */
export class FakeHub implements HubPort {
  readonly calls: CallStartRequest[] = [];
  readonly ingested: RawTranscript[] = [];
  readonly recommended: RecommendRequest[] = [];
  readonly guarded: CallGuardCheckRequest[] = [];
  readonly complianceChecked: ComplianceCheckRequest[] = [];
  /** 컴플라이언스가 잡을 표현 — 상담원 발화에 들어 있으면 findings 에 싣는다. */
  compliancePhrase = "무조건";
  failCompliance: number | null = null;
  /** 추천 응답 카드의 근거 조항을 순서대로 — 주면 `topDocId` 보다 우선한다. */
  cardDocIds: string[] | null = null;
  /** 콜 가드가 잡을 표현 — 본문에 들어 있으면 flags 에 싣는다. */
  guardPhrase = "병신";
  failGuard: number | null = null;
  /** 추천 응답 1순위 카드의 근거 조항 — 주면 cards 에 한 장 싣는다. */
  topDocId: string | null = null;
  readonly docsChecked: RequiredDocsCheckRequest[] = [];
  /** 필요서류 판정을 **물은** 조항을 순서대로 — 422 로 돌려보낸 것까지. `docsChecked` 는 판정이 돌아간 것만 담는다. */
  readonly docsAsked: string[] = [];
  /** 규칙이 없는 조항 — 서버처럼 422 를 낸다. */
  readonly notProcedures = new Set<string>();
  failIngest: number | null = null;
  failStart: number | null = null;
  readonly routed: RoutingDecisionRequest[] = [];
  failRouting: number | null = null;
  ingestDelayMs = 0;
  fired = true;

  async startCall(request: CallStartRequest): Promise<void> {
    if (this.failStart !== null) {
      throw new HubError("start", this.failStart);
    }
    this.calls.push(request);
  }

  async decideRouting(request: RoutingDecisionRequest): Promise<RoutingDecisionPayload> {
    if (this.failRouting !== null) {
      throw new HubError("routing", this.failRouting);
    }
    this.routed.push(request);
    return { call_id: request.call_id, assigned_agent_id: null, is_blacklisted: "false", fell_back: "false" };
  }

  async ingestTranscript(raw: RawTranscript): Promise<MaskedTranscript> {
    if (this.ingestDelayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.ingestDelayMs));
    }
    if (this.failIngest !== null) {
      throw new HubError("ingest", this.failIngest);
    }
    this.ingested.push(raw);
    return {
      call_id: raw.call_id,
      segment_id: String(raw.segment_id),
      speaker: raw.speaker,
      text: raw.text.replace(/\d/g, "*"),
      masked: [],
      is_final: String(raw.is_final),
      utterance_end_ms: String(raw.utterance_end_ms),
    };
  }

  async recommend(request: RecommendRequest): Promise<RecommendPayload> {
    this.recommended.push(request);
    return this.fired
      ? {
          fired: "true",
          domain: null,
          call_id: request.call_id,
          trigger_at_ms: String(request.utterance_end_ms),
          cards: (this.cardDocIds ?? (this.topDocId === null ? [] : [this.topDocId])).map((docId) => ({
            title: "t",
            summary: "s",
            source: { doc_id: docId, title: "t" },
            similarity_score: "0.9",
          })),
          internal_latency_ms: "1",
        }
      : { fired: "false", domain: null, call_id: null, trigger_at_ms: null, cards: null, internal_latency_ms: null };
  }

  async checkRequiredDocs(request: RequiredDocsCheckRequest): Promise<ClosurePayload> {
    this.docsAsked.push(request.procedure);
    if (this.notProcedures.has(request.procedure)) {
      throw new HubError("unknown procedure", 422);
    }
    this.docsChecked.push({ ...request, agent_utterances: [...request.agent_utterances] });
    const informed = request.agent_utterances.join(" ").includes("신분증");
    return {
      call_id: request.call_id,
      procedure: request.procedure,
      verdict: informed ? "complete" : "incomplete",
      missing: informed ? [] : ["신분증"],
      detected: "true",
    };
  }

  async checkCompliance(request: ComplianceCheckRequest): Promise<CompliancePayload> {
    if (this.failCompliance !== null) {
      throw new HubError("compliance", this.failCompliance);
    }
    this.complianceChecked.push(request);
    const hit = request.agent_utterance.includes(this.compliancePhrase);
    return {
      call_id: request.call_id,
      segment_id: String(request.segment_id),
      findings: hit ? [{ rule_code: "C-1", phrase: this.compliancePhrase, alternative_source: { doc_id: "DASAN-TERM-1.4", title: "권장 대체 표현" } }] : [],
    };
  }

  async checkCallGuard(request: CallGuardCheckRequest): Promise<CallGuardPayload> {
    if (this.failGuard !== null) {
      throw new HubError("guard", this.failGuard);
    }
    this.guarded.push(request);
    const at = request.customer_utterance.indexOf(this.guardPhrase);
    return {
      call_id: request.call_id,
      segment_id: String(request.segment_id),
      flags:
        at < 0
          ? []
          : [{ category: "insult", phrase: this.guardPhrase, span: [String(at), String(at + this.guardPhrase.length)], source_doc_id: "DASAN-MANUAL-5.1" }],
    };
  }
}

export class CaptureBroadcaster implements Broadcaster {
  readonly messages: Array<{ callId: string; message: CallMediatorMessage }> = [];

  publish(callId: string, message: CallMediatorMessage): void {
    this.messages.push({ callId, message });
  }

  ofType<T extends CallMediatorMessage["type"]>(type: T): Array<Extract<CallMediatorMessage, { type: T }>> {
    return this.messages
      .map((item) => item.message)
      .filter((message): message is Extract<CallMediatorMessage, { type: T }> => message.type === type);
  }
}

export class MemoryLedger implements LedgerStore {
  ledger: Record<string, number>;
  failRead = false;
  failWrite = false;

  constructor(initial: Record<string, number> = {}) {
    this.ledger = { ...initial };
  }

  async read(): Promise<Record<string, number>> {
    if (this.failRead) {
      throw new Error("broken");
    }
    return { ...this.ledger };
  }

  async add(day: string, seconds: number): Promise<Record<string, number>> {
    if (this.failWrite) {
      throw new Error("disk full");
    }
    this.ledger[day] = (this.ledger[day] ?? 0) + seconds;
    return { ...this.ledger };
  }
}

/** 16kHz PCM16 모노 n초 분량의 무음. */
export function silence(seconds: number, sampleRate = 16000): Buffer {
  return Buffer.alloc(Math.round(seconds * sampleRate) * 2);
}

export function tick(ms = 0): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 모든 말단 값이 문자열(또는 null)인가 — 대시보드 파서는 그 밖의 타입에 alert 를 띄운다. */
export function allLeavesStringOrNull(value: unknown): boolean {
  if (value === null || typeof value === "string") {
    return true;
  }
  if (Array.isArray(value)) {
    return value.every(allLeavesStringOrNull);
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).every(allLeavesStringOrNull);
  }
  return false;
}
