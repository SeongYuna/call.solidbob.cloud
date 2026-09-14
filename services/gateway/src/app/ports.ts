// Requirement: A-1, A-3, COST-1, 7.3절
/**
 * 게이트웨이가 바깥에 요구하는 것. 구현체는 `adapters/` 에 있고 `main.ts` 가 꽂는다.
 *
 * 테스트는 이 인터페이스를 가짜로 구현해 구글·서버 없이 돈다 — 서버 쪽 `hub` 포트와 같은 방식이다.
 */

export type Speaker = "customer" | "agent";

// ── STT ─────────────────────────────────────────────────────────────────────

export interface SttResult {
  text: string;
  isFinal: boolean;
  /** 채널 첫 오디오 기준 결과 끝 시각(ms). 스트림 교대가 있어도 이어진다. */
  audioEndMs: number;
}

export interface SttHandlers {
  onResult(result: SttResult): void;
  /** 되살릴 수 없는 오류. 채널을 닫아야 한다. 메시지에 전사 문자열을 넣지 않는다. */
  onFatal(message: string): void;
  /** `end()` 뒤 남은 결과를 다 보냈다. */
  onEnd(): void;
}

export interface SttStream {
  write(pcm: Buffer): void;
  /** 더 보낼 오디오가 없다. 남은 결과가 다 오면 끝난다. */
  end(): void;
}

export interface SttEngine {
  /** `call.stt_engine` 에 그대로 적힌다 — 가짜면 가짜라고 적는다. */
  readonly name: string;
  /** null 이 아니면 쓸 수 없다(키 없음 등). 채널을 열기 전에 — 서버에 통화 행을 만들기 전에 — 본다. */
  readonly unavailableReason: string | null;
  open(sampleRate: number, handlers: SttHandlers): SttStream;
}

// ── 서버 (hub) ──────────────────────────────────────────────────────────────

export interface CallStartRequest {
  call_id: string;
  stt_engine: string;
  channel_count: number;
}

/** 마스킹 **전** 원문. 게이트웨이 → 서버로만 가고 그 밖으로는 나가지 않는다 (SEC-1). */
export interface RawTranscript {
  call_id: string;
  segment_id: number;
  speaker: Speaker;
  text: string;
  is_final: boolean;
  utterance_end_ms: number;
}

/** 서버가 마스킹해 돌려준 전사 이벤트. 7.3절 계약 — 값은 전부 문자열이다(2026-09-10). */
export type MaskedTranscript = Record<string, unknown> & { text: string };

/** 마스킹 **후** 본문으로 추천을 요청한다. */
export interface RecommendRequest {
  call_id: string;
  segment_id: number;
  speaker: Speaker;
  text: string;
  is_final: boolean;
  utterance_end_ms: number;
}

export type RecommendPayload = Record<string, unknown>;

export class HubError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "HubError";
    this.status = status;
  }
}

export interface HubPort {
  startCall(request: CallStartRequest): Promise<void>;
  ingestTranscript(raw: RawTranscript): Promise<MaskedTranscript>;
  recommend(request: RecommendRequest): Promise<RecommendPayload>;
}

// ── 대시보드로 내보내기 ──────────────────────────────────────────────────────

export type GatewayMessage =
  | { type: "transcript"; payload: MaskedTranscript }
  | { type: "recommendation"; payload: RecommendPayload };

export interface Broadcaster {
  publish(callId: string, message: GatewayMessage): void;
}

// ── 사용량 장부 ─────────────────────────────────────────────────────────────

export interface LedgerStore {
  read(): Promise<Record<string, number>>;
  /** 읽고-더하고-쓴다. 배치 스크립트가 그 사이 쓴 값을 덮지 않는다. */
  add(day: string, seconds: number): Promise<Record<string, number>>;
}

export interface Logger {
  info(message: string): void;
  warn(message: string): void;
}
