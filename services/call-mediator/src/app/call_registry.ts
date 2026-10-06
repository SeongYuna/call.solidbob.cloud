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
 * **서버가 마스킹해 돌려준 응답**뿐이고, 서버가 실패하면 그 결과는 아무 데도 가지 않는다(확정은 일시 실패면
 * 몇 번 더 보낸다 — `INGEST_RETRY_DELAYS_MS`).
 * 로그에는 번호·상태 코드만 남긴다.
 */
import { SegmentCounter, OpenSegment, utteranceEndMs } from "../domain/segments.ts";
import { FirstSpeakerIsAgent } from "../domain/diarization.ts";
import { pcm16Seconds } from "../domain/budget.ts";
import type { BudgetGuard } from "./budget_guard.ts";
import { CoalescingQueue } from "./coalescing_queue.ts";
import { categoriesOf, nextIntervention } from "../domain/call_guard_intervention.ts";
import {
  HubError,
  type Broadcaster,
  type HubPort,
  type Logger,
  type MaskedTranscript,
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
   * 채널이 **모두** 닫힌 뒤 통화 상태(절차·상담원 발화·번호)를 메모리에 두는 시간(ms). 기본 `CALL_RETAIN_MS`.
   * 2026-09-30 QA 2회차에서 잡았다 — `/dev` 페이지나 대본 재생기가 화자를 바꾸려고 채널을 닫았다 열면
   * 그 사이 통화가 버려져 **F-2 절차와 상담원 발화가 사라지고 J-5 배정 판정이 두 번 기록됐다**(`_logs/2026-09-30-01`).
   * 유예 안에 다시 열면 서버 통화 행만 다시 확인하고(`POST /hub/calls`, UPSERT) 상태는 그대로 잇는다. `0` 이면 바로 버린다.
   */
  callRetainMs?: number;
  /**
   * 서버에 통화 행이 만들어진 직후 `started` 를 대시보드로 보낼까. 기본 false — 이유는
   * `announcePending` 과 같다(대시보드 파서가 모르는 `type` 에 오류 배너를 띄운다).
   * `call_id`를 잡을 다른 수단이 없는 짧은 통화의 `/close` 404 를 막는다(`w6-close-callid-missing`).
   */
  announceStarted?: boolean;
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
   * C-6 베타 — 폭언 대응 단계(`call_guard_intervention`)를 보낼까(`decisions/221`). 기본 false.
   * 꺼져 있으면 단계 판정도 하지 않는다. **켜도 통화를 끊지 않는다**(매뉴얼 5.2).
   */
  announceCallGuardIntervention?: boolean;
  /**
   * 잡힌 컴플라이언스 위반(C-1~C-4)을 `compliance` 메시지로, 검사에 실패한 발화를 `compliance_unavailable` 로
   * 대시보드에 보낼까. 기본 false — 켜기 전에 대시보드 파서(`apps/call` realCallMediatorClient)가 두 타입을 다
   * 받아야 한다. **검사는 끄지 않는다.**
   */
  announceCompliance?: boolean;
  /** J-5 배정 판정에 넘길 후보 상담사(`decisions/126`). 기본 빈 목록 — 서버가 기존 배정 규칙으로 떨어뜨린다. */
  routingCandidates?: readonly string[];
  /**
   * J-5 배정 판정 결과를 `routing_decision` 메시지로 대시보드에 보낼까. 기본 false — 이유는
   * `announcePending`과 같다. **판정 호출·저장은 끄지 않는다** — 화면 표시만의 스위치다.
   * 표시 위치·문구는 정해졌다(`decisions/407`, `w6-routing-result-ui`) — 상담원 화면에
   * "배정 판정 기록됨" 배너, "배정됐다"라고 쓰지 않는다(판정이 연결을 바꾸지 않는다).
   */
  announceRouting?: boolean;
  /**
   * F-2 필요서류 판정을 `closure` 메시지로 대시보드에 보낼까. 기본 false — 대시보드 파서가 아직 옛 종결 형식
   * (`closure_type`·`approved/blocked`)만 받는다. **판정·저장은 끄지 않는다.**
   */
  announceClosure?: boolean;
  /**
   * **확정** 전사를 서버가 받지 못했을 때(연결 실패·시간 초과·5xx·429) 다시 보내기 전 기다리는 시간들(ms). 길이 = 재시도 횟수.
   * 기본 `INGEST_RETRY_DELAYS_MS`. 테스트가 줄인다. interim 과 4xx 는 다시 보내지 않는다(`isRetryableIngestError`).
   */
  ingestRetryDelaysMs?: readonly number[];
  /**
   * F-2 — 추천 1순위 카드의 조항을 **언제** 절차로 잡나(`decisions/219`). 기본 `score-floor`
   * (= 219 가 보류 표본에서 채택한 C2, 2026-09-24). 나머지 둘은 옛 동작과 떨어진 후보를 다시 잴 때 쓴다.
   * - `score-floor` — 1순위 카드의 `similarity_score` 가 `PROCEDURE_SCORE_FLOOR` 이상일 때만 잡는다(C2, **기본**)
   * - `top1` — 추천마다 1순위 조항을 잡는다(`w6-procedure-pick-rule` — 2026-09-24 이전의 기본, C0)
   * - `two-consecutive` — **고객 발화로 발동한 추천 두 번이 연달아** 같은 1순위 조항일 때만 잡는다(C1·C3).
   *   발동하지 않은 추천(`fired` ≠ `"true"` — 상담원 발화·트리거가 거른 맞장구)은 연속을 끊지도 잇지도 않는다.
   *   **채택하지 않았다** — 보류 표본에서 필요한 절차를 8건 중 7건 잃었다
   */
  procedureAdoption?: ProcedureAdoption;
}

export type ProcedureAdoption = "top1" | "two-consecutive" | "score-floor";
export const PROCEDURE_ADOPTIONS: readonly ProcedureAdoption[] = ["top1", "two-consecutive", "score-floor"];

/**
 * C2(`score-floor`)의 하한 — `decisions/219` 사전 등록값이자 **2026-09-24 채택값**(보류 표본 12건에서 엉뚱한 쌍
 * 10 → 3, 정답 절차 손실 0). **학습 표본(`dasan-v0` 24건, 09-22 16:43 로컬 E2E)에서** 골랐다:
 * 필요서류 대본마다 「대본 절차가 1순위였던 추천」의 최고 점수를 구하고, 그 최솟값(SYN-015 초본 4.3, 0.6359)을 넘지 않게
 * 내림한 값이다 — v0 에서 C0 이 잡던 필요한 절차를 하나도 잃지 않는 가장 높은 하한. 점수 눈금은 dense(KoE5) cosine
 * `(1 + cos) / 2`(운영 구성, 리랭커 없음). 값을 바꾸려면 다시 사전 등록하고 새 표본으로 잰다 — 설정이 아니라 결정이다.
 */
export const PROCEDURE_SCORE_FLOOR = 0.635;

/**
 * 확정 전사 재시도 간격 — 처음 + 두 번 = 최대 3회. 2026-09-22 운영 SYN-010 에서 마지막 상담원 확정이 콜 미디에이터까지
 * 왔는데 서버 전사 요청 한 번이 실패해 **DB 에도 /ws 에도 남지 않았다**(`w6-replay-last-turn`). 전에는 한 번 실패로 버렸다.
 *
 * 다시 보내도 되는 근거: 서버 저장은 `(call_id, segment_id)` UPSERT 이고 마스킹 구간도 지우고 다시 넣는다(`decisions/205`,
 * `transcript_segment_repository.py`) — 첫 요청이 늦게라도 서버에서 끝났어도 행은 하나다. `POST /hub/transcripts` 는
 * 마스킹·저장 말고 다른 부작용이 없다(추천·검사는 이쪽이 응답을 받은 뒤에 따로 부른다).
 *
 * 순서: 재시도는 채널 줄(`CoalescingQueue`) **안에서** 한다 — 뒤 결과가 앞지르지 않는다. 대신 그동안 뒤 자막이 늦는다.
 * 최악(시간 초과 5초 × 3 + 1.3초)은 채널 닫기 기다림 상한(`drainTimeoutMs`, 10초)을 넘는다 — 상한은 기다림만 끊고
 * 요청은 끝까지 간다. 그 뒤에 성공해도 방송은 된다(대시보드 구독은 채널과 무관하다).
 */
export const INGEST_RETRY_DELAYS_MS: readonly number[] = [300, 1_000];

/** 채널이 모두 닫힌 뒤 통화 상태를 잇는 유예 — 화자를 바꾸느라 채널을 닫았다 여는 데 5분이면 넉넉하다. */
export const CALL_RETAIN_MS = 5 * 60_000;

/** 다시 보내면 달라질 수 있는 실패인가. 4xx(401 토큰·409 통화 없음·422 계약)는 다시 보내도 같다. */
export function isRetryableIngestError(error: unknown): boolean {
  if (!(error instanceof HubError)) {
    return true; // 응답 본문 해석 실패 등 — 서버 쪽 일시 문제로 본다(UPSERT 라 다시 보내도 해가 없다)
  }
  return error.status === null || error.status === 429 || error.status >= 500;
}

interface CallState {
  readonly callId: string;
  /** C-6 베타 — 이 통화에서 폭언이 잡힌 고객 발화 수. 메모리에만 둔다(`decisions/221` 6절). */
  abuseCount: number;
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
  /**
   * `two-consecutive` 전용 — 고객 확정 발화마다 보낸 추천의 1순위 조항(발화 번호 순). 추천은 줄 밖에서 동시에 돌아
   * 응답 순서가 발화 순서와 다를 수 있어서, 응답을 받기 전(`pending`)에도 자리를 잡아 둔다 — 사이의 응답이 아직 안 왔으면
   * 「연달아」를 판정하지 않는다. `skip` 은 발동하지 않았거나 실패한 추천이다(연속에서 빠진다).
   */
  readonly customerTops: Map<number, TopEntry>;
  /** 채널이 모두 닫힌 뒤 상태를 버리기까지의 타이머. 채널이 하나라도 열려 있으면 `null`. */
  retainTimer: NodeJS.Timeout | null;
  /** J-5 배정 판정을 이미 불렀나 — 유예 안에 다시 연 통화에서 두 번 기록하지 않는다. */
  routed: boolean;
}

type TopEntry = { state: "pending" } | { state: "skip" } | { state: "done"; docId: string | null };

export class CallRegistry {
  private readonly deps: RegistryDeps;
  private readonly calls = new Map<string, CallState>();

  constructor(deps: RegistryDeps) {
    this.deps = deps;
  }

  /** 채널이 하나라도 열린 통화 수 — 유예 중(채널 0)인 통화는 세지 않는다(`/health` 의 `active_calls`). */
  get activeCalls(): number {
    let n = 0;
    for (const call of this.calls.values()) {
      if (call.channels.size > 0) {
        n += 1;
      }
    }
    return n;
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
      this.drop(call);
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
      if (found.retainTimer !== null) {
        // 유예 중이던 통화 — 상태(절차·상담원 발화·번호)는 잇고, 서버 통화 행만 다시 확인한다(닫혔을 수 있다).
        clearTimeout(found.retainTimer);
        found.retainTimer = null;
        this.deps.log.info(`통화 유예에서 이어감 call=${spec.callId} 절차=${found.procedures.size} 상담원 발화=${found.agentFinals.length}`);
        this.startOnServer(found, spec);
      }
      return found;
    }
    const call: CallState = {
      callId: spec.callId,
      abuseCount: 0,
      startedAtMs: this.deps.nowMs(),
      counter: new SegmentCounter(),
      channels: new Map(),
      started: Promise.resolve(false),
      procedures: new Set(),
      notProcedures: new Set(),
      agentFinals: [],
      closureChain: Promise.resolve(),
      customerTops: new Map(),
      retainTimer: null,
      routed: false,
    };
    this.calls.set(spec.callId, call);
    this.startOnServer(call, spec);
    // J-5 — 통화 행이 생긴 직후 배정 판정(`decisions/126`). **시연용 대리다** — 완성본은 교환기가 연결 전에 부른다(`320`).
    // 교환기가 붙으면 이 호출을 지운다(안 지우면 판정이 두 번 기록된다). `started` 에 묶지 않는다 — 전사를 기다리게 하지 않고,
    // 실패해도 통화는 막지 않는다(배정은 얇은 필터다, `204`). 2026-09-23 화면 표시 정했다 — `announceRouting`(`w6-routing-result-ui`).
    // 유예 안에 다시 연 통화는 여기를 지나지 않는다 — 판정은 통화당 한 번이다(`routed`).
    void call.started.then((started) => {
      if (started && !call.routed) {
        call.routed = true;
        return this.decideRouting(spec.callId);
      }
      return undefined;
    });
    return call;
  }

  /** 서버에 통화 행을 만들거나(처음) 다시 확인한다(유예에서 이어감) — `POST /hub/calls` 는 UPSERT 다. */
  private startOnServer(call: CallState, spec: ChannelSpec): void {
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
        (result) => {
          // 다시 연 통화면 저장된 번호 뒤에서 센다 — 채널은 `started` 를 기다린 뒤에 번호를 받으므로 첫 발화 전에 끝난다
          if (result.lastSegmentId > 0) {
            call.counter.resumeAfter(result.lastSegmentId);
            this.deps.log.info(`통화 다시 열림 call=${spec.callId} 발화 번호 ${result.lastSegmentId + 1} 부터`);
          }
          if (this.deps.announceStarted ?? false) {
            this.deps.broadcaster.publish(spec.callId, {
              type: "started",
              payload: { call_id: spec.callId },
            });
          }
          return true;
        },
        (error: unknown) => {
          this.deps.log.warn(`통화 시작 실패 call=${spec.callId} status=${statusOf(error)}`);
          return false;
        },
      );
  }

  private async decideRouting(callId: string): Promise<void> {
    try {
      const d = await this.deps.hub.decideRouting({ call_id: callId, candidates: [...(this.deps.routingCandidates ?? [])] });
      this.deps.log.info(
        `배정 판정 call=${callId} assigned=${String(d.assigned_agent_id ?? "-")} blacklisted=${String(d.is_blacklisted)} fell_back=${String(d.fell_back)}`,
      );
      if (this.deps.announceRouting ?? false) {
        this.deps.broadcaster.publish(callId, { type: "routing_decision", payload: d });
      }
    } catch (error: unknown) {
      this.deps.log.warn(`배정 판정 실패 call=${callId} status=${statusOf(error)}`);
    }
  }

  /** 채널이 모두 닫혔으면 유예 타이머를 건다 — 유예가 끝나야 버린다(`callRetainMs`). */
  private dropIfEmpty(call: CallState): void {
    if (call.channels.size !== 0 || this.calls.get(call.callId) !== call || call.retainTimer !== null) {
      return;
    }
    const retainMs = this.deps.callRetainMs ?? CALL_RETAIN_MS;
    if (retainMs <= 0) {
      this.drop(call);
      return;
    }
    const timer = setTimeout(() => {
      call.retainTimer = null;
      this.drop(call);
    }, retainMs);
    timer.unref?.();
    call.retainTimer = timer;
  }

  private drop(call: CallState): void {
    if (call.retainTimer !== null) {
      clearTimeout(call.retainTimer);
      call.retainTimer = null;
    }
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
    const masked = await this.ingest(item);
    if (masked === null) {
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
   * 서버에 전사를 보내 마스킹본을 받는다. **확정**이 일시 실패하면 `ingestRetryDelaysMs` 만큼 기다려 다시 보낸다
   * (`INGEST_RETRY_DELAYS_MS` 주석). 끝내 못 받으면 `null` — 마스킹을 못 거친 결과는 어디에도 보내지 않는다(SEC-1).
   * 로그에는 통화·발화 번호·상태·시도 횟수만 남긴다. 원문은 남기지 않는다.
   */
  private async ingest(item: QueuedResult): Promise<MaskedTranscript | null> {
    const delays = item.isFinal ? (this.deps.ingestRetryDelaysMs ?? INGEST_RETRY_DELAYS_MS) : [];
    const where = `call=${this.callId} segment=${item.segmentId}`;
    for (let attempt = 1; ; attempt += 1) {
      try {
        return await this.deps.hub.ingestTranscript(item.raw);
      } catch (error) {
        const status = statusOf(error);
        const delay = delays[attempt - 1];
        if (!item.isFinal) {
          this.deps.log.warn(`전사 전달 실패 ${where} status=${status} — 대시보드로 보내지 않는다(interim)`);
          return null;
        }
        if (delay === undefined || !isRetryableIngestError(error)) {
          this.deps.log.warn(
            `전사 전달 포기 ${where} status=${status} (${attempt}회 시도) — 확정 발화가 저장·대시보드 어디에도 가지 않는다`,
          );
          return null;
        }
        this.deps.log.warn(`전사 전달 실패 ${where} status=${status} — ${delay}ms 뒤 다시 보낸다 (${attempt}/${delays.length + 1})`);
        await new Promise((resolve) => setTimeout(resolve, delay));
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
    // **여기서 잡지 않으면 프로세스가 죽는다.** Node 는 처리되지 않은 rejection 을 기본으로 throw 한다.
    // 안쪽 함수들이 각자 try/catch 를 하고 있지만 그 **밖**(방송·정리)에서 던지는 경우가 남아 있었고,
    // 그 한 줄이 통화 중인 모든 채널을 끊는다. 한 통화의 실패가 미디에이터 전체를 내리지 않게 막는다(2026-09-24).
    const task = work
      .catch((error: unknown) => {
        this.deps.log.warn(`통화 작업 실패 call=${this.callId} ${error instanceof Error ? error.message : String(error)}`);
      })
      .finally(() => this.inflight.delete(task));
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
      if (this.deps.announceCallGuardIntervention === true) {
        const intervention = nextIntervention(this.call.abuseCount, categoriesOf(payload.flags));
        if (intervention !== null) {
          this.call.abuseCount = intervention.abuseCount;
          this.deps.broadcaster.publish(this.callId, {
            type: "call_guard_intervention",
            payload: {
              call_id: this.callId,
              segment_id: String(item.segmentId),
              stage: intervention.stage,
              abuse_count: String(intervention.abuseCount),
              pause_ms: String(intervention.pauseMs),
              announcement: intervention.announcement,
              source_doc_id: intervention.sourceDocId,
              beta: "true",
            },
          });
          this.deps.log.info(`C-6 베타 대응 call=${this.callId} segment=${item.segmentId} stage=${intervention.stage} 횟수=${intervention.abuseCount}`);
        }
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
    const mode = this.deps.procedureAdoption ?? "score-floor";
    const tracksStreak = mode === "two-consecutive" && item.raw.speaker === "customer";
    if (tracksStreak) {
      this.call.customerTops.set(item.segmentId, { state: "pending" });
    }
    let payload: RecommendPayload;
    try {
      payload = await this.deps.hub.recommend({
        call_id: this.callId,
        segment_id: item.segmentId,
        speaker: item.raw.speaker,
        text: maskedText,
        is_final: true,
        utterance_end_ms: item.raw.utterance_end_ms,
        received_at_ms: item.receivedAtMs,
      });
    } catch (error) {
      this.deps.log.warn(`추천 요청 실패 call=${this.callId} segment=${item.segmentId} status=${statusOf(error)}`);
      if (tracksStreak) {
        this.call.customerTops.set(item.segmentId, { state: "skip" });
        this.adoptStreaks();
      }
      return;
    }
    this.deps.broadcaster.publish(this.callId, {
      type: "recommendation",
      // `call_id` 를 **늘** 싣는다. 서버는 트리거가 안 걸린 응답(`fired:false`)에 call_id 를 담지 않는데(계약대로다),
      // 화면 파서는 없는 값을 `""` 로 채워 스토어의 통화 ID 를 덮어쓴다 → `/close` 가 404 가 되고 요약·확정 버튼이 사라진다.
      // 지금까지는 뒤따라오는 `closure` 가 ID 를 되살려 가려져 있었는데, 점수 하한(`decisions/219`)으로 **절차를 하나도
      // 안 잡는 통화**가 생기면서 그 복구 경로가 없어졌다(2026-09-24 교차 검수). 미디에이터는 통화 ID 를 알고 있으므로
      // 여기서 채운다 — 서버가 실을 때와 같은 값이다(`cards.call_id = event.call_id`). 화면 쪽 수정(`w6-close-callid-missing`,
      // 조서희)은 그대로 필요하다. 이건 그 버그가 **상시로 터지는 것**만 막는다
      // ⚠ `call_id` 를 **뒤에** 쓴다 — 서버는 트리거가 안 걸리면 이 키를 빼는 게 아니라 **`null` 로 싣는다.**
      // 앞에 두면 그 null 이 덮어써서 아무 효과가 없다(2026-09-24 테스트가 잡았다). 값은 서버가 실을 때와 같다
      //
      // `segment_id` 도 같은 이유로 여기서 싣는다(2026-09-28, `w6-per-utterance-no-docs`) — **어느 발화의 추천인지**가
      // 서버 응답(`RecommendResponse`)에 없다. 화면은 `fired: true, cards: []`(B-6 관련 문서 없음)를 **그 발화 줄 밑에**
      // 그리려는데 붙일 자리를 몰랐다. `trigger_at_ms` 는 수신 시각이라 발화와 1:1 이 아니고, 화면에서 추정하면
      // 엉뚱한 줄에 붙는다. 미디에이터는 어느 세그먼트로 요청했는지 알고 있다 — `recommendation_pending` 이 이미 같은 키를 싣는다.
      // 화면 파서는 **선택 필드**로 읽어 없으면 아무것도 안 그린다(조서희, PR #153) — 옛 미디에이터와도 깨지지 않는다.
      payload: {
        ...withE2eLatency(payload, item.raw.utterance_end_ms, this.callClockMs()),
        call_id: this.callId,
        segment_id: String(item.segmentId),
      },
    });
    const candidate = topSourceDocId(payload);
    if (mode === "top1") {
      if (candidate !== null) {
        this.track(this.adoptProcedure(candidate));
      }
    } else if (mode === "score-floor") {
      const score = topSimilarityScore(payload);
      if (candidate !== null && score !== null && score >= PROCEDURE_SCORE_FLOOR) {
        this.track(this.adoptProcedure(candidate));
      } else if (candidate !== null) {
        // **왜 안 잡았는지 남긴다.** 하한은 dense(KoE5) 눈금에 맞춘 값이라, 검색이 BM25 로 내려가거나 리랭커가 켜지면
        // 점수 눈금이 통째로 달라져 하한이 조용히 무의미해진다(늘 통과하거나 늘 막힌다). 그때 「필요서류가 안 떠요」와
        // 구분할 단서가 이 줄뿐이다 — 점수가 없으면(`null`) 눈금이 아니라 **필드가 안 온 것**이다
        this.deps.log.warn(
          `절차 미채택 call=${this.callId} segment=${item.segmentId} doc=${candidate} score=${score ?? "없음"} 하한=${PROCEDURE_SCORE_FLOOR}`,
        );
      }
    } else if (tracksStreak) {
      this.call.customerTops.set(
        item.segmentId,
        payload["fired"] === "true" ? { state: "done", docId: candidate } : { state: "skip" },
      );
      this.adoptStreaks();
    }
  }

  /**
   * `two-consecutive` — 발동한 고객 추천을 발화 번호 순으로 늘어놓고, **이웃한 둘이 모두 응답을 받았고 1순위 조항이 같으면**
   * 그 조항을 잡는다. 사이에 아직 응답이 안 온 추천이 있으면 그 쌍은 보지 않는다(그 응답이 올 때 다시 본다).
   * 이미 잡았거나 규칙이 없다고 들은 조항은 `adoptProcedure` 가 다시 묻지 않는다 — 여러 번 불러도 된다.
   */
  private adoptStreaks(): void {
    const entries = [...this.call.customerTops.entries()]
      .filter(([, entry]) => entry.state !== "skip")
      .sort(([a], [b]) => a - b)
      .map(([, entry]) => entry);
    for (let i = 1; i < entries.length; i += 1) {
      const prev = entries[i - 1]!;
      const cur = entries[i]!;
      if (prev.state === "done" && cur.state === "done" && cur.docId !== null && prev.docId === cur.docId) {
        this.track(this.adoptProcedure(cur.docId));
      }
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

/** 1순위 카드의 `similarity_score`(7.3절 — 문자열). 없거나 숫자가 아니면 `null` — 하한을 넘었다고 치지 않는다. */
function topSimilarityScore(payload: Record<string, unknown>): number | null {
  const cards = payload["cards"];
  if (!Array.isArray(cards) || cards.length === 0) {
    return null;
  }
  const raw = (cards[0] as { similarity_score?: unknown } | null)?.similarity_score;
  const score = typeof raw === "number" ? raw : typeof raw === "string" && raw.trim() !== "" ? Number(raw) : Number.NaN;
  return Number.isFinite(score) ? score : null;
}

function statusOf(error: unknown): string {
  if (error instanceof HubError) {
    return error.status === null ? "연결 실패" : String(error.status);
  }
  return "알 수 없음";
}
