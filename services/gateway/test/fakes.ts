// Requirement: QUA-1
/** 테스트용 가짜 포트 — 구글·서버 없이 파이프라인을 돌린다. */
import {
  HubError,
  type Broadcaster,
  type CallStartRequest,
  type GatewayMessage,
  type HubPort,
  type LedgerStore,
  type Logger,
  type MaskedTranscript,
  type RawTranscript,
  type RecommendPayload,
  type RecommendRequest,
  type SttEngine,
  type SttHandlers,
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
  bytes = 0;
  ended = false;

  constructor(sampleRate: number, handlers: SttHandlers) {
    this.sampleRate = sampleRate;
    this.handlers = handlers;
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

  emit(text: string, isFinal: boolean, audioEndMs: number): void {
    this.handlers.onResult({ text, isFinal, audioEndMs });
  }
}

export class FakeStt implements SttEngine {
  readonly name = "fake-stt";
  unavailableReason: string | null = null;
  readonly streams: FakeSttStream[] = [];

  open(sampleRate: number, handlers: SttHandlers): SttStream {
    const stream = new FakeSttStream(sampleRate, handlers);
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
  failIngest: number | null = null;
  failStart: number | null = null;
  ingestDelayMs = 0;
  fired = true;

  async startCall(request: CallStartRequest): Promise<void> {
    if (this.failStart !== null) {
      throw new HubError("start", this.failStart);
    }
    this.calls.push(request);
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
          cards: [],
          internal_latency_ms: "1",
        }
      : { fired: "false", domain: null, call_id: null, trigger_at_ms: null, cards: null, internal_latency_ms: null };
  }
}

export class CaptureBroadcaster implements Broadcaster {
  readonly messages: Array<{ callId: string; message: GatewayMessage }> = [];

  publish(callId: string, message: GatewayMessage): void {
    this.messages.push({ callId, message });
  }

  ofType(type: GatewayMessage["type"]): GatewayMessage[] {
    return this.messages.filter((item) => item.message.type === type).map((item) => item.message);
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
