// Requirement: A-1, A-4
/**
 * Google Cloud Speech-to-Text v1 스트리밍.
 *
 * 설정은 V4 측정(`scripts/test_stt_v4_streaming.py`)과 **같다** — LINEAR16 · `ko-KR` · interim 켬.
 * 거기서 잰 지연(첫 interim 962ms, 발화 종료 후 final +346ms)이 이 경로의 기준선이라,
 * 모델·옵션을 바꾸면 그 수치를 다시 재야 한다.
 *
 * A-4 발화 구간은 구글 끝점 검출에 맡긴다 — `is_final` 이 발화 경계다. 따로 VAD 를 두지 않는다.
 *
 * **스트림 한 개는 약 5분이 한도다**(구글이 `OUT_OF_RANGE` 로 끊는다). 통화는 그보다 길 수 있어
 * 교대한다: 오디오가 `rotateAfterMs` 를 넘기면 다음 final 에서, `hardLimitMs` 를 넘기면 즉시
 * 새 스트림을 연다. 옛 스트림은 이미 받은 오디오의 결과를 마저 보낸 뒤 닫힌다. 결과 시각은
 * 스트림마다 0 부터 세므로 **그 스트림이 열리기 전까지 보낸 오디오 길이**를 더해 이어 붙인다.
 *
 * 오디오가 한동안 안 오면(음소거 등) 구글이 같은 `OUT_OF_RANGE` 로 끊는다. 그때는 다음 오디오가
 * 올 때 새로 연다 — 채널을 닫지 않는다.
 */
import { EventEmitter } from "node:events";
import speech from "@google-cloud/speech";
import type { SttEngine, SttHandlers, SttStream } from "../app/ports.ts";

/** 구글 스트림에서 이 어댑터가 쓰는 부분만. 테스트는 이것을 가짜로 만든다. */
export interface RecognizeStream extends EventEmitter {
  write(chunk: Buffer): boolean;
  end(): void;
}

export type RecognizeStreamFactory = (sampleRate: number) => RecognizeStream;

export interface RotationOptions {
  rotateAfterMs: number;
  hardLimitMs: number;
}

/** 구글 권장 한 메시지 오디오 상한은 25KB 다. 넉넉히 자른다. */
const MAX_CHUNK_BYTES = 15_000;
/** gRPC OUT_OF_RANGE — 스트림 시간 한도·무음 타임아웃. 채널을 닫지 않고 다시 연다. */
const OUT_OF_RANGE = 11;

export function googleStreamFactory(): RecognizeStreamFactory {
  const client = new speech.SpeechClient();
  return (sampleRate) =>
    client.streamingRecognize({
      config: {
        encoding: "LINEAR16",
        sampleRateHertz: sampleRate,
        languageCode: "ko-KR",
      },
      interimResults: true,
    }) as unknown as RecognizeStream;
}

export class GoogleSttEngine implements SttEngine {
  readonly name = "google-stt";
  readonly unavailableReason = null;
  private readonly factory: RecognizeStreamFactory;
  private readonly rotation: RotationOptions;

  constructor(factory: RecognizeStreamFactory, rotation: RotationOptions = { rotateAfterMs: 240_000, hardLimitMs: 280_000 }) {
    this.factory = factory;
    this.rotation = rotation;
  }

  open(sampleRate: number, handlers: SttHandlers): SttStream {
    return new RotatingStream(this.factory, sampleRate, this.rotation, handlers);
  }
}

interface Leg {
  stream: RecognizeStream;
  /** 이 스트림이 열리기 전까지 채널이 보낸 오디오(ms). */
  baseMs: number;
  done: boolean;
}

class RotatingStream implements SttStream {
  private readonly factory: RecognizeStreamFactory;
  private readonly sampleRate: number;
  private readonly rotation: RotationOptions;
  private readonly handlers: SttHandlers;
  private readonly legs = new Set<Leg>();
  private current: Leg | null = null;
  private sentMs = 0;
  private ended = false;
  private endNotified = false;
  private fatal = false;

  constructor(factory: RecognizeStreamFactory, sampleRate: number, rotation: RotationOptions, handlers: SttHandlers) {
    this.factory = factory;
    this.sampleRate = sampleRate;
    this.rotation = rotation;
    this.handlers = handlers;
  }

  write(pcm: Buffer): void {
    if (this.ended || this.fatal) {
      return;
    }
    for (let offset = 0; offset < pcm.byteLength; offset += MAX_CHUNK_BYTES) {
      const chunk = pcm.subarray(offset, Math.min(offset + MAX_CHUNK_BYTES, pcm.byteLength));
      if (this.current !== null && this.sentMs - this.current.baseMs >= this.rotation.hardLimitMs) {
        this.retire(this.current);
      }
      const leg = this.current ?? this.openLeg();
      leg.stream.write(chunk);
      this.sentMs += (chunk.byteLength / (this.sampleRate * 2)) * 1000;
    }
  }

  end(): void {
    if (this.ended) {
      return;
    }
    this.ended = true;
    if (this.current !== null) {
      this.retire(this.current);
    }
    this.maybeNotifyEnd();
  }

  private openLeg(): Leg {
    const leg: Leg = { stream: this.factory(this.sampleRate), baseMs: this.sentMs, done: false };
    this.legs.add(leg);
    this.current = leg;
    leg.stream.on("data", (response: unknown) => this.onData(leg, response));
    leg.stream.on("error", (error: unknown) => this.onError(leg, error));
    leg.stream.on("end", () => this.finish(leg));
    leg.stream.on("close", () => this.finish(leg));
    return leg;
  }

  /** 더 이상 오디오를 보내지 않는다. 받은 오디오의 결과는 마저 받는다. */
  private retire(leg: Leg): void {
    if (this.current === leg) {
      this.current = null;
    }
    leg.stream.end();
  }

  /**
   * 응답 하나의 `results` 는 **final 0~1개 + interim 여러 개**다(구글 `StreamingRecognizeResponse`).
   * interim 들은 한 가설을 «안정된 앞부분 / 흔들리는 뒷부분» 으로 나눈 조각이라 **이어 붙여야
   * 전체 문장**이다. 조각마다 따로 흘리면 같은 발화 번호로 서로 덮어써 뒷조각만 화면에 남는다
   * (2026-09-11 실측 — "로미 기프트콘" 다음에 " 쓰고 다른" 이 와서 앞이 사라졌다).
   */
  private onData(leg: Leg, response: unknown): void {
    const results = ((response as { results?: unknown[] } | null)?.results ?? []) as GoogleResult[];
    const finals = results.filter((result) => result.isFinal === true);
    const interims = results.filter((result) => result.isFinal !== true);

    for (const result of finals) {
      this.handlers.onResult({ text: transcriptOf(result), isFinal: true, audioEndMs: this.endOf(leg, result) });
    }
    if (interims.length > 0) {
      const text = interims.map(transcriptOf).join("");
      const last = interims[interims.length - 1]!;
      this.handlers.onResult({ text, isFinal: false, audioEndMs: this.endOf(leg, last) });
    }
    if (finals.length > 0 && this.current === leg && this.sentMs - leg.baseMs >= this.rotation.rotateAfterMs) {
      this.retire(leg); // 발화 경계에서 갈아타면 문장이 두 스트림에 쪼개지지 않는다
    }
  }

  private endOf(leg: Leg, result: GoogleResult): number {
    return leg.baseMs + (durationMs(result.resultEndTime) ?? this.sentMs - leg.baseMs);
  }

  private onError(leg: Leg, error: unknown): void {
    const code = (error as { code?: unknown } | null)?.code;
    if (code === OUT_OF_RANGE) {
      // 시간 한도·무음 타임아웃. 다음 오디오에서 새로 연다.
      if (this.current === leg) {
        this.current = null;
      }
      this.finish(leg);
      return;
    }
    this.finish(leg);
    if (!this.fatal) {
      this.fatal = true;
      // 구글 오류 본문을 그대로 옮기지 않는다 — 상태 코드만 넘긴다.
      this.handlers.onFatal(`구글 STT 스트림 오류 code=${String(code ?? "?")}`);
      this.ended = true;
      if (this.current !== null) {
        this.retire(this.current);
      }
      this.maybeNotifyEnd();
    }
  }

  private finish(leg: Leg): void {
    if (leg.done) {
      return;
    }
    leg.done = true;
    this.legs.delete(leg);
    if (this.current === leg) {
      this.current = null;
    }
    leg.stream.removeAllListeners("data");
    // error 리스너는 남긴다 — 닫힌 뒤 오는 오류가 처리되지 않은 예외로 프로세스를 죽이지 않게.
    leg.stream.on("error", () => {});
    this.maybeNotifyEnd();
  }

  private maybeNotifyEnd(): void {
    if (this.ended && !this.endNotified && this.legs.size === 0) {
      this.endNotified = true;
      this.handlers.onEnd();
    }
  }
}

interface GoogleResult {
  isFinal?: boolean;
  alternatives?: Array<{ transcript?: string }>;
  resultEndTime?: { seconds?: number | string | { toString(): string }; nanos?: number };
}

function transcriptOf(result: GoogleResult): string {
  return result.alternatives?.[0]?.transcript ?? "";
}

function durationMs(value: { seconds?: number | string | { toString(): string }; nanos?: number } | undefined): number | null {
  if (value === undefined || value === null) {
    return null;
  }
  const seconds = Number(value.seconds === undefined ? 0 : String(value.seconds));
  const nanos = value.nanos ?? 0;
  if (!Number.isFinite(seconds)) {
    return null;
  }
  return seconds * 1000 + nanos / 1e6;
}
