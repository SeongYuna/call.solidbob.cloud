// Requirement: A-1, A-2, A-3, COST-1, SEC-1
/**
 * 통화와 채널을 들고 파이프라인을 잇는다 — 오디오 → STT → 서버(마스킹·저장) → 대시보드.
 *
 * **채널 = 화자 하나.** V1 실측이 전부 모노라 화자 분리는 채널로 한다(데모의 물리 2채널, A-2).
 * 한 통화에 `agent`·`customer` 채널이 하나씩 붙을 수 있고, 발화 번호는 통화 안에서 하나로 센다.
 *
 * 채널의 입력은 둘이다(`ChannelSpec.source`).
 * - `audio` — PCM 을 받아 구글 STT 로 전사한다. COST-1 캡을 쓴다
 * - `text`  — 브라우저가 이미 글자로 바꿔 보낸다(`/dev`, Web Speech API — `decisions/109`, 402 에서 옮김).
 *             구글을 부르지 않으므로 캡을 쓰지 않는다. 통화 기록에는 엔진을 사실대로 `web-speech` 로 적는다
 *
 * SEC-1 — 원문(`RawTranscript`)은 `hub.ingestTranscript` 에만 들어간다. 대시보드로 가는 것은
 * **서버가 마스킹해 돌려준 응답**뿐이고, 서버가 실패하면 그 결과는 아무 데도 가지 않는다.
 * 로그에는 번호·상태 코드만 남긴다.
 */
import { SegmentCounter, OpenSegment, utteranceEndMs } from "../domain/segments.ts";
import { pcm16Seconds } from "../domain/budget.ts";
import type { BudgetGuard } from "./budget_guard.ts";
import { CoalescingQueue } from "./coalescing_queue.ts";
import {
  HubError,
  type Broadcaster,
  type HubPort,
  type Logger,
  type RawTranscript,
  type Speaker,
  type SttEngine,
  type SttResult,
  type SttStream,
} from "./ports.ts";

export interface ChannelSpec {
  callId: string;
  speaker: Speaker;
  sampleRate: number;
  /** 이 통화에 붙을 채널 수(1 = 모노, 2 = 물리 분리). `call.channel_count` 로 간다. */
  channelCount: number;
  /** 기본 `audio`. `text` 는 브라우저 음성 인식 결과(글자)를 받는다. */
  source?: "audio" | "text";
}

/** 글자 입력 채널이 `call.stt_engine` 에 적는 이름 — 구글 STT 가 아니라는 것을 기록에 남긴다. */
export const TEXT_ENGINE_NAME = "web-speech";

export type OpenResult =
  | { ok: true; channel: Channel }
  | { ok: false; kind: "budget" | "busy" | "unavailable"; reason: string };

export interface RegistryDeps {
  hub: HubPort;
  stt: SttEngine;
  budget: BudgetGuard;
  broadcaster: Broadcaster;
  log: Logger;
  nowMs: () => number;
  /** 채널을 닫을 때 남은 결과를 기다리는 최대 시간. */
  drainTimeoutMs?: number;
}

interface CallState {
  readonly callId: string;
  readonly startedAtMs: number;
  readonly counter: SegmentCounter;
  readonly channels: Map<Speaker, Channel>;
  started: Promise<boolean>;
}

export class CallRegistry {
  private readonly deps: RegistryDeps;
  private readonly calls = new Map<string, CallState>();

  constructor(deps: RegistryDeps) {
    this.deps = deps;
  }

  get activeCalls(): number {
    return this.calls.size;
  }

  async open(spec: ChannelSpec): Promise<OpenResult> {
    const existing = this.calls.get(spec.callId);
    if (existing?.channels.has(spec.speaker)) {
      return { ok: false, kind: "busy", reason: `이 통화의 ${spec.speaker} 채널이 이미 열려 있다` };
    }

    // 글자 입력은 구글을 부르지 않는다 — 키도 캡도 보지 않는다.
    if ((spec.source ?? "audio") === "audio") {
      if (this.deps.stt.unavailableReason !== null) {
        return { ok: false, kind: "unavailable", reason: this.deps.stt.unavailableReason };
      }
      const decision = await this.deps.budget.decideOpen();
      if (!decision.ok) {
        return { ok: false, kind: "budget", reason: decision.reason };
      }
    }

    const call = this.callFor(spec);
    if (!(await call.started)) {
      this.dropIfEmpty(call);
      return { ok: false, kind: "unavailable", reason: "서버에 통화를 열지 못했다(POST /hub/calls)" };
    }
    // 기다리는 사이 같은 화자가 먼저 붙었을 수 있다.
    if (call.channels.has(spec.speaker)) {
      return { ok: false, kind: "busy", reason: `이 통화의 ${spec.speaker} 채널이 이미 열려 있다` };
    }

    const channel = new Channel(call, spec, this.deps, () => {
      call.channels.delete(spec.speaker);
      this.dropIfEmpty(call);
    });
    call.channels.set(spec.speaker, channel);
    return { ok: true, channel };
  }

  /** 서버에 통화 행을 먼저 만든다 — `transcript_segment.call_id` 외래키(decisions/301). */
  private callFor(spec: ChannelSpec): CallState {
    const found = this.calls.get(spec.callId);
    if (found !== undefined) {
      return found;
    }
    const call: CallState = {
      callId: spec.callId,
      startedAtMs: this.deps.nowMs(),
      counter: new SegmentCounter(),
      channels: new Map(),
      started: Promise.resolve(false),
    };
    this.calls.set(spec.callId, call);
    const engine = (spec.source ?? "audio") === "text" ? TEXT_ENGINE_NAME : this.deps.stt.name;
    call.started = this.deps.hub
      .startCall({ call_id: spec.callId, stt_engine: engine, channel_count: spec.channelCount })
      .then(
        () => true,
        (error: unknown) => {
          this.deps.log.warn(`통화 시작 실패 call=${spec.callId} status=${statusOf(error)}`);
          return false;
        },
      );
    return call;
  }

  private dropIfEmpty(call: CallState): void {
    if (call.channels.size === 0 && this.calls.get(call.callId) === call) {
      this.calls.delete(call.callId);
    }
  }
}

interface QueuedResult {
  segmentId: number;
  isFinal: boolean;
  raw: RawTranscript;
}

export class Channel {
  readonly callId: string;
  readonly speaker: Speaker;
  private readonly spec: ChannelSpec;
  private readonly deps: RegistryDeps;
  private readonly channelStartMs: number;
  private readonly openedAtMs: number;
  private readonly isText: boolean;
  private readonly segment: OpenSegment;
  private readonly queue: CoalescingQueue<QueuedResult>;
  private readonly stt: SttStream;
  private readonly onDetach: () => void;
  private readonly inflight = new Set<Promise<void>>();
  private readonly stopListeners: Array<(reason: string) => void> = [];
  private closed = false;
  private sttEnded: Promise<void>;
  private resolveSttEnded: () => void = () => {};
  private closing: Promise<void> | null = null;

  constructor(call: CallState, spec: ChannelSpec, deps: RegistryDeps, onDetach: () => void) {
    this.callId = spec.callId;
    this.speaker = spec.speaker;
    this.spec = spec;
    this.deps = deps;
    this.onDetach = onDetach;
    this.openedAtMs = deps.nowMs();
    this.channelStartMs = this.openedAtMs - call.startedAtMs;
    this.isText = spec.source === "text";
    this.segment = new OpenSegment(call.counter);
    this.queue = new CoalescingQueue((item) => this.forward(item));
    this.sttEnded = new Promise((resolve) => {
      this.resolveSttEnded = resolve;
    });
    this.stt = this.isText
      ? // 글자 채널은 열 STT 가 없다. 끝낼 때 기다릴 것도 없다.
        { write: () => {}, end: () => this.resolveSttEnded() }
      : deps.stt.open(spec.sampleRate, {
          onResult: (result) => this.onResult(result),
          onFatal: (message) => this.stop(`STT 오류 — ${message}`),
          onEnd: () => this.resolveSttEnded(),
        });
  }

  /** 채널이 스스로 닫힐 때(캡 도달·STT 오류) 이유를 받는다. 소켓을 닫는 데 쓴다. */
  onStop(listener: (reason: string) => void): void {
    this.stopListeners.push(listener);
  }

  /** false 면 이 오디오를 보내지 않았고 채널이 닫혔다. */
  pushAudio(pcm: Buffer): boolean {
    if (this.closed || this.isText) {
      return false;
    }
    if (!this.deps.budget.consume(pcm16Seconds(pcm.byteLength, this.spec.sampleRate))) {
      this.stop("STT 사용량 한도에 닿아 채널을 닫는다(COST-1)");
      return false;
    }
    this.stt.write(pcm);
    return true;
  }

  /**
   * 글자 채널 — 브라우저가 인식한 결과 하나. 오디오 채널의 STT 결과와 **같은 길**로 간다(서버 마스킹 →
   * 대시보드). 발화 종료 시각은 브라우저가 아니라 이 서버가 받은 시각으로 센다 — 믿을 수 있는 쪽을 쓴다.
   */
  pushText(text: string, isFinal: boolean): boolean {
    if (this.closed || !this.isText) {
      return false;
    }
    this.onResult({ text, isFinal, audioEndMs: this.deps.nowMs() - this.openedAtMs });
    return true;
  }

  /** 생산자가 끝냈다. 남은 결과를 서버·대시보드까지 보내고 풀린다. */
  close(): Promise<void> {
    if (this.closing !== null) {
      return this.closing;
    }
    this.closed = true;
    this.stt.end();
    this.closing = this.drain();
    return this.closing;
  }

  private stop(reason: string): void {
    if (this.closed) {
      return;
    }
    this.deps.log.warn(`채널 중단 call=${this.callId} speaker=${this.speaker} — ${reason}`);
    void this.close();
    for (const listener of this.stopListeners) {
      listener(reason);
    }
  }

  private async drain(): Promise<void> {
    const timeoutMs = this.deps.drainTimeoutMs ?? 10_000;
    let timer: NodeJS.Timeout | undefined;
    const timeout = new Promise<void>((resolve) => {
      timer = setTimeout(resolve, timeoutMs);
    });
    try {
      await Promise.race([
        (async () => {
          await this.sttEnded;
          await this.queue.whenIdle();
          await Promise.all([...this.inflight]);
        })(),
        timeout,
      ]);
    } finally {
      clearTimeout(timer);
      await this.deps.budget.flush();
      this.onDetach();
    }
  }

  private onResult(result: SttResult): void {
    const segmentId = this.segment.idFor(result.isFinal);
    if (result.text.trim().length === 0) {
      return;
    }
    this.queue.push({
      segmentId,
      isFinal: result.isFinal,
      raw: {
        call_id: this.callId,
        segment_id: segmentId,
        speaker: this.speaker,
        text: result.text,
        is_final: result.isFinal,
        utterance_end_ms: utteranceEndMs(this.channelStartMs, result.audioEndMs),
      },
    });
  }

  private async forward(item: QueuedResult): Promise<void> {
    let masked;
    try {
      masked = await this.deps.hub.ingestTranscript(item.raw);
    } catch (error) {
      // 마스킹을 못 거친 결과는 어디에도 보내지 않는다 (SEC-1). 원문을 로그에 남기지 않는다.
      this.deps.log.warn(
        `전사 전달 실패 call=${this.callId} segment=${item.segmentId} status=${statusOf(error)} — 대시보드로 보내지 않는다`,
      );
      return;
    }
    this.deps.broadcaster.publish(this.callId, { type: "transcript", payload: masked });

    if (item.isFinal && masked.text.trim().length > 0) {
      const task = this.recommend(item, masked.text).finally(() => this.inflight.delete(task));
      this.inflight.add(task);
    }
  }

  /**
   * 트리거 v1 은 final 도착 기반이다(`w3-trigger-v1`). 판정은 서버가 하고 여기서는 **마스킹된 본문**
   * 을 넘기기만 한다. 다음 자막을 막지 않도록 줄 밖에서 돈다.
   */
  private async recommend(item: QueuedResult, maskedText: string): Promise<void> {
    try {
      const payload = await this.deps.hub.recommend({
        call_id: this.callId,
        segment_id: item.segmentId,
        speaker: this.speaker,
        text: maskedText,
        is_final: true,
        utterance_end_ms: item.raw.utterance_end_ms,
      });
      this.deps.broadcaster.publish(this.callId, { type: "recommendation", payload });
    } catch (error) {
      this.deps.log.warn(`추천 요청 실패 call=${this.callId} segment=${item.segmentId} status=${statusOf(error)}`);
    }
  }
}

function statusOf(error: unknown): string {
  if (error instanceof HubError) {
    return error.status === null ? "연결 실패" : String(error.status);
  }
  return "알 수 없음";
}
