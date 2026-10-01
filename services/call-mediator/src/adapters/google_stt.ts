// Requirement: A-1, A-4
/**
 * Google Cloud Speech-to-Text v1 스트리밍.
 *
 * 설정은 V4 측정(`scripts/test_stt_v4_streaming.py`)과 **같다** — LINEAR16 · `ko-KR` · interim 켬.
 * 거기서 잰 지연(첫 interim 962ms, 발화 종료 후 final +346ms)이 이 경로의 기준선이라,
 * 모델·옵션을 바꾸면 그 수치를 다시 재야 한다.
 *
 * A-4 발화 구간 — ~~구글 끝점 검출에 맡긴다~~ **로컬 에너지 끝점 검출을 둔다(2026-10-01).** 기본 모델·ko-KR 스트리밍은
 * 발화 사이 10초 무음에도 final 을 주지 않고 **스트림이 끝날 때 한 번** 줬다(운영 실측 — `google-stt` 통화 5건 전부 화자당
 * final 1개, `real-stt-01` 은 60초 네 턴이 한 줄). 그래서 말한 뒤 `silenceMs` 만큼 조용하면 스트림을 닫아 final 을 받고,
 * 다음 소리에서 새 스트림을 연다(교대 로직 그대로). 무음 구간은 보내지 않아 STT 캡(COST-1)도 아낀다.
 * 화자 분리(`speaker=auto`)는 끝점 검출을 끈다 — 스트림마다 화자 번호가 새로 매겨져 구간을 이을 수 없다.
 *
 * **스트림 한 개는 약 5분이 한도다**(구글이 `OUT_OF_RANGE` 로 끊는다). 통화는 그보다 길 수 있어
 * 교대한다: 오디오가 `rotateAfterMs` 를 넘기면 다음 final 에서, `hardLimitMs` 를 넘기면 즉시
 * 새 스트림을 연다. 옛 스트림은 이미 받은 오디오의 결과를 마저 보낸 뒤 닫힌다. 결과 시각은
 * 스트림마다 0 부터 세므로 **그 스트림이 열리기 전까지 보낸 오디오 길이**를 더해 이어 붙인다.
 *
 * 오디오가 한동안 안 오면(음소거 등) 구글이 같은 `OUT_OF_RANGE` 로 끊는다. 그때는 다음 오디오가
 * 올 때 새로 연다 — 채널을 닫지 않는다.
 *
 * **화자 분리(`diarize`, `speaker=auto` 채널만 — `decisions/303`)** 를 켜면 단어 시각·화자 라벨을 요청하고,
 * final 결과를 **화자가 바뀌는 곳마다 잘라** `speakerLabel` 을 붙여 보낸다. 구글은 응답마다 처음부터의 단어를
 * 다시 보내므로 이미 보낸 끝 시각 뒤의 단어만 친다(`domain/diarization.ts`). 설정이 V4 측정과 달라지므로
 * 이 채널의 지연은 V4 수치로 인용하지 않는다.
 */
import { EventEmitter } from "node:events";
import speech from "@google-cloud/speech";
import type { SttEngine, SttHandlers, SttOpenOptions, SttStream } from "../app/ports.ts";
import { newRuns, type TaggedWord } from "../domain/diarization.ts";

/** 구글 스트림에서 이 어댑터가 쓰는 부분만. 테스트는 이것을 가짜로 만든다. */
export interface RecognizeStream extends EventEmitter {
  write(chunk: Buffer): boolean;
  end(): void;
}

export type RecognizeStreamFactory = (sampleRate: number, diarize: boolean) => RecognizeStream;

export interface RotationOptions {
  rotateAfterMs: number;
  hardLimitMs: number;
  /** A-4 로컬 끝점 검출. 없으면(테스트·화자 분리) 구글에 맡긴다 — 그러면 final 은 스트림 끝에만 온다. */
  endpoint?: EndpointOptions | null;
}

/** 발화 끝 판정 — 소리의 RMS(int16) 로만 본다. 모델도 네트워크도 없다. */
export interface EndpointOptions {
  /** 이 RMS 미만이면 무음. 디지털 무음 0 · 조용한 방 50~200 · 말소리 1,000~5,000 */
  threshold: number;
  /** 말한 뒤 이만큼 무음이 이어지면 발화 끝 */
  silenceMs: number;
  /** 이보다 짧은 소리는 발화로 치지 않는다(기침·클릭) */
  minSpeechMs: number;
}

export const DEFAULT_ENDPOINT: EndpointOptions = { threshold: 400, silenceMs: 700, minSpeechMs: 250 };

/** 청크의 RMS(int16 LE). */
export function rmsOf(chunk: Buffer): number {
  const n = Math.floor(chunk.byteLength / 2);
  if (n === 0) {
    return 0;
  }
  let sum = 0;
  for (let i = 0; i < n; i += 1) {
    const v = chunk.readInt16LE(i * 2);
    sum += v * v;
  }
  return Math.sqrt(sum / n);
}

/** 구글 권장 한 메시지 오디오 상한은 25KB 다. 넉넉히 자른다. */
const MAX_CHUNK_BYTES = 15_000;
/** gRPC OUT_OF_RANGE — 스트림 시간 한도·무음 타임아웃. 채널을 닫지 않고 다시 연다. */
const OUT_OF_RANGE = 11;

export function googleStreamFactory(): RecognizeStreamFactory {
  const client = new speech.SpeechClient();
  return (sampleRate, diarize) =>
    client.streamingRecognize({
      config: {
        encoding: "LINEAR16",
        sampleRateHertz: sampleRate,
        languageCode: "ko-KR",
        ...(diarize
          ? {
              enableWordTimeOffsets: true,
              diarizationConfig: { enableSpeakerDiarization: true, minSpeakerCount: 2, maxSpeakerCount: 2 },
            }
          : {}),
      },
      interimResults: true,
    }) as unknown as RecognizeStream;
}

export class GoogleSttEngine implements SttEngine {
  readonly name = "google-stt";
  readonly unavailableReason = null;
  private readonly factory: RecognizeStreamFactory;
  private readonly rotation: RotationOptions;

  constructor(
    factory: RecognizeStreamFactory,
    rotation: RotationOptions = { rotateAfterMs: 240_000, hardLimitMs: 280_000, endpoint: DEFAULT_ENDPOINT },
  ) {
    this.factory = factory;
    this.rotation = rotation;
  }

  open(sampleRate: number, handlers: SttHandlers, options: SttOpenOptions = {}): SttStream {
    return new RotatingStream(this.factory, sampleRate, this.rotation, handlers, options.diarize === true);
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
  private readonly diarize: boolean;
  /** 화자 분리 — 이 시각(채널 기준 ms)까지 끝난 단어는 이미 보냈다. */
  private diarizedUntilMs = 0;
  /** 끝점 검출 — 지금 스트림에서 들린 말소리(ms) · 마지막 말소리 뒤 이어진 무음(ms). */
  private speechMs = 0;
  private silenceRunMs = 0;

  constructor(
    factory: RecognizeStreamFactory,
    sampleRate: number,
    rotation: RotationOptions,
    handlers: SttHandlers,
    diarize: boolean,
  ) {
    this.factory = factory;
    this.sampleRate = sampleRate;
    this.rotation = rotation;
    this.handlers = handlers;
    this.diarize = diarize;
  }

  write(pcm: Buffer): void {
    if (this.ended || this.fatal) {
      return;
    }
    const endpoint = this.diarize ? null : (this.rotation.endpoint ?? null);
    for (let offset = 0; offset < pcm.byteLength; offset += MAX_CHUNK_BYTES) {
      const chunk = pcm.subarray(offset, Math.min(offset + MAX_CHUNK_BYTES, pcm.byteLength));
      const chunkMs = (chunk.byteLength / (this.sampleRate * 2)) * 1000;
      if (this.current !== null && this.sentMs - this.current.baseMs >= this.rotation.hardLimitMs) {
        this.retire(this.current);
      }
      if (endpoint !== null) {
        const loud = rmsOf(chunk) >= endpoint.threshold;
        if (loud) {
          this.speechMs += chunkMs;
          this.silenceRunMs = 0;
        } else {
          this.silenceRunMs += chunkMs;
        }
        if (this.current !== null && this.speechMs >= endpoint.minSpeechMs && this.silenceRunMs >= endpoint.silenceMs) {
          this.retire(this.current); // 발화 끝 — 스트림을 닫아야 구글이 final 을 돌려준다
          this.speechMs = 0;
        }
        if (this.current === null && !loud) {
          this.sentMs += chunkMs; // 무음은 보내지 않는다 — 시각만 흐른다
          continue;
        }
      }
      const leg = this.current ?? this.openLeg();
      leg.stream.write(chunk);
      this.sentMs += chunkMs;
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
    const leg: Leg = { stream: this.factory(this.sampleRate, this.diarize), baseMs: this.sentMs, done: false };
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
      if (this.diarize) {
        this.emitDiarized(leg, result);
        continue;
      }
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

  /**
   * final 하나를 화자 구간마다 나눠 보낸다. 단어 정보가 없으면(구글이 안 줬으면) 라벨 없이 통째로 보낸다 —
   * 누구 말인지 모르는 결과를 어떻게 할지는 채널이 정한다.
   */
  private emitDiarized(leg: Leg, result: GoogleResult): void {
    const words: TaggedWord[] = [];
    for (const info of result.alternatives?.[0]?.words ?? []) {
      const endMs = durationMs(info.endTime);
      if (endMs === null) {
        continue;
      }
      const label = (info.speakerLabel ?? "").trim() || (info.speakerTag ? String(info.speakerTag) : "");
      words.push({ word: info.word ?? "", endMs: leg.baseMs + endMs, label: label || null });
    }
    if (words.length === 0) {
      this.handlers.onResult({ text: transcriptOf(result), isFinal: true, audioEndMs: this.endOf(leg, result) });
      return;
    }
    for (const run of newRuns(words, this.diarizedUntilMs)) {
      this.handlers.onResult({ text: run.text, isFinal: true, audioEndMs: run.endMs, speakerLabel: run.label });
      this.diarizedUntilMs = Math.max(this.diarizedUntilMs, run.endMs);
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

type GoogleDuration = { seconds?: number | string | { toString(): string }; nanos?: number };

interface GoogleResult {
  isFinal?: boolean;
  alternatives?: Array<{
    transcript?: string;
    words?: Array<{ word?: string; endTime?: GoogleDuration; speakerTag?: number; speakerLabel?: string }>;
  }>;
  resultEndTime?: GoogleDuration;
}

function transcriptOf(result: GoogleResult): string {
  return result.alternatives?.[0]?.transcript ?? "";
}

function durationMs(value: GoogleDuration | undefined): number | null {
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
