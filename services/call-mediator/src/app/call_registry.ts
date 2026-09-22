// Requirement: A-1, A-2, A-3, C-1, C-6, F-2, COST-1, SEC-1
/**
 * 통화와 채널을 들고 파이프라인을 잇는다 — 오디오 → STT → 서버(마스킹·저장) → 대시보드.
 *
 * **채널 = 화자 하나.** V1 실측이 전부 모노라 화자 분리는 채널로 한다(데모의 물리 2채널, A-2).
 * 한 통화에 `agent`·`customer` 채널이 하나씩 붙을 수 있고, 발화 번호는 통화 안에서 하나로 센다.
 *
 * **`speaker: "auto"`** — 모노 녹음에 두 사람이 섞여 있을 때. 구글 화자 분리를 켜고 **먼저 말한 화자를 상담원**으로
 * 친다(`domain/diarization.ts`, `decisions/303`). 추측이라 기본값이 아니고, 통화 기록의 엔진 이름에 `+diarize` 를
 * 붙여 남긴다. 이 채널은 그 통화의 두 화자를 다 차지한다. 화자 라벨이 없는 결과(interim 전부)는 보내지 않는다
 * — 누구 말인지 모르는 자막을 상담원·고객 어느 쪽으로도 지어내지 않는다.
 *
 * 채널의 입력은 둘이다(`ChannelSpec.source`).
 * - `audio` — PCM 을 받아 구글 STT 로 전사한다. COST-1 캡을 쓴다
 * - `text`  — 브라우저가 이미 글자로 바꿔 보낸다(`/dev`, Web Speech API — `decisions/109`, 402 에서 옮김).
 *             구글을 부르지 않으므로 캡을 쓰지 않는다. 통화 기록에는 엔진을 사실대로 `web-speech` 로 적는다.
 *             합성 대본 재생기(`textProducer: "script"`)도 이 문으로 들어오고, 엔진은 `synthetic-script` 로 적는다 —
 *             사람의 말을 받아쓴 것이 아니라는 것을 기록에 남긴다
 *
 * SEC-1 — 원문(`RawTranscript`)은 `hub.ingestTranscript` 에만 들어간다. 대시보드로 가는 것은
 * **서버가 마스킹해 돌려준 응답**뿐이고, 서버가 실패하면 그 결과는 아무 데도 가지 않는다.
 * 로그에는 번호·상태 코드만 남긴다.
 */
import { SegmentCounter, OpenSegment, utteranceEndMs } from "../domain/segments.ts";
import { FirstSpeakerIsAgent } from "../domain/diarization.ts";
import { pcm16Seconds } from "../domain/budget.ts";
import type { BudgetGuard } from "./budget_guard.ts";
import { CoalescingQueue } from "./coalescing_queue.ts";
import {
  HubError,
  type Broadcaster,
  type HubPort,
  type Logger,
  type RawTranscript,
  type RecommendPayload,
  type Speaker,
  type SttEngine,
  type SttResult,
  type SttStream,
} from "./ports.ts";

/** 채널이 맡는 화자. `auto` 는 모노 한 줄의 두 화자를 구글 화자 분리로 가른다(오디오 채널만). */
export type ChannelSpeaker = Speaker | "auto";

export interface ChannelSpec {
  callId: string;
  speaker: ChannelSpeaker;
  sampleRate: number;
  /** 이 통화에 붙을 채널 수(1 = 모노, 2 = 물리 분리). `call.channel_count` 로 간다. */
  channelCount: number;
  /** 기본 `audio`. `text` 는 브라우저 음성 인식 결과(글자)를 받는다. */
  source?: "audio" | "text";
  /** 글자 채널을 누가 채우나 — 기본 `web-speech`. 통화 기록 엔진 이름만 가른다. */
  textProducer?: TextProducer;
  /**
   * 발신 번호(선택) — 통화를 **처음 여는** 채널의 것만 서버로 간다(통화 시작은 한 번). 재상담 이력·블랙리스트가
   * 고객을 잇는 재료다(`decisions/304`). ⚠ 평문이다 — 로그·대시보드로 보내지 않는다.
   */
  callerPhone?: string;
}

/** 글자 입력 채널이 `call.stt_engine` 에 적는 이름 — 구글 STT 가 아니라는 것을 기록에 남긴다. */
export const TEXT_ENGINE_NAME = "web-speech";
/** 합성 대본 재생(`scripts/persona_sim/`)이 적는 이름 — 사람도 STT 도 거치지 않았다. */
export const SCRIPT_ENGINE_NAME = "synthetic-script";

export type TextProducer = "web-speech" | "script";
/** 화자 분리 채널이 엔진 이름 뒤에 붙인다 — 화자가 추측이라는 것을 통화 기록에 남긴다(`call.stt_engine` 30자 안). */
export const DIARIZE_ENGINE_SUFFIX = "+diarize";

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
  /**
   * 추천 요청 직전에 `recommendation_pending` 을 대시보드로 보낼까. 기본 false —
   * `apps/call` 의 실서버 파서가 모르는 `type` 에 오류 배너를 띄워서, 수신 코드가 들어가기 전에 켜면
   * 라이브 화면이 깨진다(`w4-recommendation-pending-contract`).
   */
  announcePending?: boolean;
  /**
   * 잡힌 콜 가드 신호(C-6)를 `call_guard` 메시지로 대시보드에 보낼까. 기본 false — 이유는 `announcePending` 과 같다.
   * **검사·저장은 끄지 않는다** — 서버가 `call_guard_flag` 에 남기는 것은 화면과 무관하게 돈다.
   */
  announceCallGuard?: boolean;
  /**
   * 잡힌 컴플라이언스 위반(C-1~C-4)을 `compliance` 메시지로, 검사에 실패한 발화를 `compliance_unavailable` 로
   * 대시보드에 보낼까. 기본 false — 켜기 전에 대시보드 파서(`apps/call` realCallMediatorClient)가 두 타입을 다
   * 받아야 한다. **검사는 끄지 않는다.**
   */
  announceCompliance?: boolean;
  /** J-5 배정 판정에 넘길 후보 상담사(`decisions/126`). 기본 빈 목록 — 서버가 기존 배정 규칙으로 떨어뜨린다. */
  routingCandidates?: readonly string[];
  /**
   * F-2 필요서류 판정을 `closure` 메시지로 대시보드에 보낼까. 기본 false — 대시보드 파서가 아직 옛 종결 형식
   * (`closure_type`·`approved/blocked`)만 받는다. **판정·저장은 끄지 않는다.**
   */
  announceClosure?: boolean;
}

interface CallState {
  readonly callId: string;
  readonly startedAtMs: number;
  readonly counter: SegmentCounter;
  readonly channels: Map<ChannelSpeaker, Channel>;
  started: Promise<boolean>;
  /**
   * F-2 — 이 통화에서 판정 중인 절차(필요서류 조항 ID). 추천 **1순위 카드**의 조항 중 서버가 규칙을 아는 것이다
   * (`adoptProcedure`). 서버가 규칙이 없다고 한(422) 조항은 `notProcedures` 로 옮겨 다시 묻지 않는다.
   */
  readonly procedures: Set<string>;
  readonly notProcedures: Set<string>;
  /** 상담원 확정 발화 **마스킹본** — 서버 판정 입력. 원문은 여기 없다(SEC-1). */
  readonly agentFinals: string[];
  /** 판정 요청을 한 줄로 세운다 — 늦게 보낸 요청의 응답이 먼저 와서 화면이 옛 판정으로 되돌아가지 않게. */
  closureChain: Promise<void>;
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
    if (spec.speaker === "auto" && spec.source === "text") {
      return { ok: false, kind: "unavailable", reason: "화자 분리(auto)는 오디오 채널만 된다" };
    }
    const existing = this.calls.get(spec.callId);
    if (existing !== undefined && conflicts(existing, spec.speaker)) {
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
    if (conflicts(call, spec.speaker)) {
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
      procedures: new Set(),
      notProcedures: new Set(),
      agentFinals: [],
      closureChain: Promise.resolve(),
    };
    this.calls.set(spec.callId, call);
    const engine =
      (spec.source ?? "audio") === "text"
        ? spec.textProducer === "script"
          ? SCRIPT_ENGINE_NAME
          : TEXT_ENGINE_NAME
        : `${this.deps.stt.name}${spec.speaker === "auto" ? DIARIZE_ENGINE_SUFFIX : ""}`;
    call.started = this.deps.hub
      .startCall({
        call_id: spec.callId,
        stt_engine: engine,
        channel_count: spec.channelCount,
        ...(spec.callerPhone ? { caller_phone: spec.callerPhone } : {}),
      })
      .then(
        () => true,
        (error: unknown) => {
          this.deps.log.warn(`통화 시작 실패 call=${spec.callId} status=${statusOf(error)}`);
          return false;
        },
      );
    // J-5 — 통화 행이 생긴 직후 배정 판정(`decisions/126`). **시연용 대리다** — 완성본은 교환기가 연결 전에 부른다(`320`).
    // 교환기가 붙으면 이 호출을 지운다(안 지우면 판정이 두 번 기록된다). `started` 에 묶지 않는다 — 전사를 기다리게 하지 않고,
    // 실패해도 통화는 막지 않는다(배정은 얇은 필터다, `204`). 결과는 로그에만 — 화면 표시는 조서희 님과 정한 뒤다.
    void call.started.then((started) => (started ? this.decideRouting(spec.callId) : undefined));
    return call;
  }

  private async decideRouting(callId: string): Promise<void> {
    try {
      const d = await this.deps.hub.decideRouting({ call_id: callId, candidates: [...(this.deps.routingCandidates ?? [])] });
      this.deps.log.info(
        `배정 판정 call=${callId} assigned=${String(d.assigned_agent_id ?? "-")} blacklisted=${String(d.is_blacklisted)} fell_back=${String(d.fell_back)}`,
      );
    } catch (error: unknown) {
      this.deps.log.warn(`배정 판정 실패 call=${callId} status=${statusOf(error)}`);
    }
  }

  private dropIfEmpty(call: CallState): void {
    if (call.channels.size === 0 && this.calls.get(call.callId) === call) {
      this.calls.delete(call.callId);
    }
  }
}

/** `auto` 는 두 화자를 다 차지한다 — 같은 통화에 다른 채널과 함께 열리지 않는다. */
function conflicts(call: CallState, speaker: ChannelSpeaker): boolean {
  if (call.channels.has(speaker) || call.channels.has("auto")) {
    return true;
  }
  return speaker === "auto" && call.channels.size > 0;
}

interface QueuedResult {
  segmentId: number;
  isFinal: boolean;
  raw: RawTranscript;
  /** STT 결과를 받은 시각(통화 시작 기준 ms). 서버 대기·마스킹 시간을 섞지 않으려고 줄에 넣기 전에 잰다. */
  receivedAtMs: number;
}

export class Channel {
  private readonly call: CallState;
  readonly callId: string;
  readonly speaker: ChannelSpeaker;
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
  /** `auto` 채널만 — 화자 라벨 → 상담원·고객. */
  private readonly speakers: FirstSpeakerIsAgent | null;
  private readonly stopListeners: Array<(reason: string) => void> = [];
  private closed = false;
  private sttEnded: Promise<void>;
  private resolveSttEnded: () => void = () => {};
  private closing: Promise<void> | null = null;

  constructor(call: CallState, spec: ChannelSpec, deps: RegistryDeps, onDetach: () => void) {
    this.call = call;
    this.callId = spec.callId;
    this.speaker = spec.speaker;
    this.spec = spec;
    this.deps = deps;
    this.onDetach = onDetach;
    this.openedAtMs = deps.nowMs();
    this.channelStartMs = this.openedAtMs - call.startedAtMs;
    this.isText = spec.source === "text";
    this.segment = new OpenSegment(call.counter);
    this.speakers = spec.speaker === "auto" ? new FirstSpeakerIsAgent() : null;
    this.queue = new CoalescingQueue((item) => this.forward(item));
    this.sttEnded = new Promise((resolve) => {
      this.resolveSttEnded = resolve;
    });
    this.stt = this.isText
      ? // 글자 채널은 열 STT 가 없다. 끝낼 때 기다릴 것도 없다.
        { write: () => {}, end: () => this.resolveSttEnded() }
      : deps.stt.open(
          spec.sampleRate,
          {
            onResult: (result) => this.onResult(result),
            onFatal: (message) => this.stop(`STT 오류 — ${message}`),
            onEnd: () => this.resolveSttEnded(),
          },
          { diarize: this.speakers !== null },
        );
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
    let speaker: Speaker;
    if (this.speakers === null) {
      speaker = this.speaker as Speaker;
    } else if (result.speakerLabel !== undefined) {
      speaker = this.speakers.speakerOf(result.speakerLabel);
    } else {
      if (result.isFinal) {
        this.deps.log.warn(`화자 라벨 없는 final 을 버렸다 call=${this.callId} — 누구 말인지 지어내지 않는다`);
      }
      return; // interim 은 라벨이 없다 — auto 채널은 final 만 흘린다
    }
    const segmentId = this.segment.idFor(result.isFinal);
    if (result.text.trim().length === 0) {
      return;
    }
    this.queue.push({
      segmentId,
      isFinal: result.isFinal,
      receivedAtMs: this.callClockMs(),
      raw: {
        call_id: this.callId,
        segment_id: segmentId,
        speaker,
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
      this.track(this.recommend(item, masked.text));
      if (item.raw.speaker === "customer") {
        this.track(this.checkCallGuard(item, masked.text));
      } else {
        // C-1~C-4 — 상담원 발화만 검사한다(고객 발화는 C-6). 판정·저장은 서버 몫
        this.track(this.checkCompliance(item, masked.text));
        // F-2 — 상담원이 서류를 안내했을 수 있다. 판정 중인 절차를 전부 다시 본다
        this.call.agentFinals.push(masked.text);
        for (const procedure of this.call.procedures) {
          this.track(this.checkRequiredDocs(procedure));
        }
      }
    }
  }

  /**
   * F-2 — 절차 하나를 지금까지의 상담원 발화로 판정한다. 판정(누락이 무엇인가)은 서버 규칙이 한다.
   * 한 통화의 요청은 줄을 세워 순서대로 보낸다 — 응답이 뒤집혀 화면이 옛 판정으로 돌아가지 않게.
   */
  private checkRequiredDocs(procedure: string): Promise<void> {
    const utterances = [...this.call.agentFinals];
    const run = async (): Promise<void> => {
      if (this.call.notProcedures.has(procedure)) {
        return;
      }
      try {
        const payload = await this.deps.hub.checkRequiredDocs({
          call_id: this.callId,
          procedure,
          agent_utterances: utterances,
        });
        if (this.deps.announceClosure === true) {
          this.deps.broadcaster.publish(this.callId, { type: "closure", payload });
        }
      } catch (error) {
        if (error instanceof HubError && error.status === 422) {
          // 규칙이 없는 조항(필요서류 조항이 아니거나 조건 분기로 제외된 것) — 절차가 아니다. 다시 묻지 않는다
          this.call.procedures.delete(procedure);
          this.call.notProcedures.add(procedure);
          return;
        }
        this.deps.log.warn(`필요서류 판정 실패 call=${this.callId} procedure=${procedure} status=${statusOf(error)}`);
      }
    };
    const next = this.call.closureChain.then(run);
    this.call.closureChain = next;
    return next;
  }

  private track(work: Promise<void>): void {
    const task = work.finally(() => this.inflight.delete(task));
    this.inflight.add(task);
  }

  /**
   * C-6 — 고객 final 의 **마스킹된 본문**을 검사한다. 판정·저장은 서버가 한다. 화자로 거르는 것은 판정이 아니라
   * 계약이다(검사 대상이 고객 발화뿐 — 상담원 발화는 C-1~C-4 몫). 다음 자막을 막지 않도록 줄 밖에서 돈다.
   */
  private async checkCallGuard(item: QueuedResult, maskedText: string): Promise<void> {
    try {
      const payload = await this.deps.hub.checkCallGuard({
        call_id: this.callId,
        segment_id: item.segmentId,
        customer_utterance: maskedText,
      });
      if (this.deps.announceCallGuard === true && payload.flags.length > 0) {
        this.deps.broadcaster.publish(this.callId, { type: "call_guard", payload });
      }
    } catch (error) {
      this.deps.log.warn(`콜 가드 검사 실패 call=${this.callId} segment=${item.segmentId} status=${statusOf(error)}`);
    }
  }

  /**
   * C-1~C-4 — 상담원 final 의 **마스킹된 본문**을 검사한다. 판정은 서버 규칙이 한다. 화자로 거르는 것은 판정이 아니라
   * 계약이다(검사 대상이 상담원 발화뿐). 실패해도 통화는 계속된다. 다음 자막을 막지 않도록 줄 밖에서 돈다.
   *
   * 화면이 받는 신호는 셋이다 — 위반이 잡히면 `compliance`, 검사가 실패하면 `compliance_unavailable`, 검사가 돌았는데
   * 잡힌 게 없으면 **아무것도 안 보낸다.** 실패를 「메시지 없음」에 섞으면 탐지가 죽은 것이 「위반 없음」으로 보인다
   * (2026-09-22 조서희 요청 — 그전엔 둘이 구분되지 않았다).
   */
  private async checkCompliance(item: QueuedResult, maskedText: string): Promise<void> {
    try {
      const payload = await this.deps.hub.checkCompliance({
        call_id: this.callId,
        segment_id: item.segmentId,
        agent_utterance: maskedText,
      });
      if (this.deps.announceCompliance === true && payload.findings.length > 0) {
        this.deps.broadcaster.publish(this.callId, { type: "compliance", payload });
      }
    } catch (error) {
      const status = statusOf(error);
      this.deps.log.warn(`컴플라이언스 검사 실패 call=${this.callId} segment=${item.segmentId} status=${status}`);
      if (this.deps.announceCompliance === true) {
        this.deps.broadcaster.publish(this.callId, {
          type: "compliance_unavailable",
          payload: { call_id: this.callId, segment_id: String(item.segmentId), status },
        });
      }
    }
  }

  /**
   * F-2 — 추천 **1순위 카드**의 조항만 절차 후보로 본다(`w6-procedure-pick-rule`, 2026-09-22 정성윤·류준 합의).
   * 서버가 규칙을 알면(판정이 돌아오면) 절차로 잡고, 「절차 아님」(422 — 규칙 없는 조항·`TERM` 이 아닌 조항)이면
   * **이 추천에서는 아무것도 잡지 않는다.** 2순위 아래로 내려가지 않는다.
   *
   * 전에는 422 를 건너뛰고 다음 카드로 내려가 「규칙 있는 첫 조항」을 잡았다. 1순위가 정답인데 규칙이 없으면
   * 한참 아래 카드의 엉뚱한 절차를 잡아 틀린 「빠진 서류」를 띄웠다 — 09-22 운영 SYN-010(1순위 `TERM-2.12` 규칙 없음 →
   * 5순위 `TERM-2.9` 채택 → `incomplete`「신분증」), 로컬 E2E 24건 중 23건(오판 75건). 판정 안 함이 틀린 판정보다 낫다.
   * 판정 중인 절차는 그대로 둔다(누적 — 빼는 것은 화면과 맞춰야 해서 이 티켓 밖이다).
   */
  private async adoptProcedure(candidate: string): Promise<void> {
    if (this.call.procedures.has(candidate) || this.call.notProcedures.has(candidate)) {
      return; // 이미 판정 중이거나 규칙이 없다고 들은 조항 — 다시 묻지 않는다
    }
    this.call.procedures.add(candidate);
    await this.checkRequiredDocs(candidate); // 422 면 checkRequiredDocs 가 procedures 에서 빼고 notProcedures 로 옮긴다
  }

  /**
   * 트리거 v1 은 final 도착 기반이다(`w3-trigger-v1`). 판정은 서버가 하고 여기서는 **마스킹된 본문**
   * 을 넘기기만 한다. 다음 자막을 막지 않도록 줄 밖에서 돈다.
   */
  /** 통화 시작 기준 ms — `utterance_end_ms`·`received_at_ms` 와 **같은 시계**다. 서로 뺄 수 있어야 해서 한 곳에 둔다. */
  private callClockMs(): number {
    return Math.max(0, this.deps.nowMs() - this.openedAtMs + this.channelStartMs);
  }

  private async recommend(item: QueuedResult, maskedText: string): Promise<void> {
    if (this.deps.announcePending === true) {
      this.deps.broadcaster.publish(this.callId, {
        type: "recommendation_pending",
        payload: { call_id: this.callId, segment_id: String(item.segmentId) },
      });
    }
    try {
      const payload = await this.deps.hub.recommend({
        call_id: this.callId,
        segment_id: item.segmentId,
        speaker: item.raw.speaker,
        text: maskedText,
        is_final: true,
        utterance_end_ms: item.raw.utterance_end_ms,
        received_at_ms: item.receivedAtMs,
      });
      this.deps.broadcaster.publish(this.callId, {
        type: "recommendation",
        payload: withE2eLatency(payload, item.raw.utterance_end_ms, this.callClockMs()),
      });
      const candidate = topSourceDocId(payload);
      if (candidate !== null) {
        this.track(this.adoptProcedure(candidate));
      }
    } catch (error) {
      this.deps.log.warn(`추천 요청 실패 call=${this.callId} segment=${item.segmentId} status=${statusOf(error)}`);
    }
  }
}

/**
 * `e2e_latency_ms` = 발화 종료 → **방송 직전** (`_project/decisions/119`).
 *
 * 서버 DTO·DB 컬럼은 2026-09-09 부터 있었는데 **아무도 값을 넣지 않아 늘 null 이었다** — 서버는 방송 시각을 모른다.
 * 그 시각을 아는 곳이 여기 하나라 여기서 채운다. **브라우저가 그리는 시간은 들어 있지 않다**(재지 않기로 했다).
 * - 발동하지 않은 응답(`fired: "false"`)에는 넣지 않는다 — 카드가 없으면 「표시까지」가 없다
 * - `utterance_end_ms` 가 없으면 넣지 않는다. 0 으로 지어내지 않는다(절대 원칙 2)
 * - 서버 응답이 그렇듯 **문자열**로 싣는다(7.3절 — 값은 전부 문자열)
 * ⚠ 합성 통화(`/dev/text`)는 STT 를 안 거쳐 이 값이 실제보다 짧다 — 보고할 때 「STT 미경유」를 붙인다(`decisions/209`).
 */
export function withE2eLatency(
  payload: RecommendPayload,
  utteranceEndMs: number | null | undefined,
  broadcastAtMs: number,
): RecommendPayload {
  if (payload["fired"] !== "true" || typeof utteranceEndMs !== "number" || !Number.isFinite(utteranceEndMs)) {
    return payload;
  }
  return { ...payload, e2e_latency_ms: String(Math.max(0, Math.round(broadcastAtMs - utteranceEndMs))) };
}

/**
 * 추천 응답 **1순위 카드**의 근거 조항 ID. 카드가 없거나 1순위 카드의 모양이 다르면 `null` — 2순위로 내려가지 않는다.
 * 절차를 지어내지 않는다(`w6-procedure-pick-rule`).
 */
function topSourceDocId(payload: Record<string, unknown>): string | null {
  const cards = payload["cards"];
  if (!Array.isArray(cards) || cards.length === 0) {
    return null;
  }
  const source = (cards[0] as { source?: { doc_id?: unknown } } | null)?.source;
  return typeof source?.doc_id === "string" && source.doc_id.length > 0 ? source.doc_id : null;
}

function statusOf(error: unknown): string {
  if (error instanceof HubError) {
    return error.status === null ? "연결 실패" : String(error.status);
  }
  return "알 수 없음";
}
