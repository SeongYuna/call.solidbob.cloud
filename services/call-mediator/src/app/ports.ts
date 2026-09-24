// Requirement: A-1, A-3, COST-1, 7.3절
/**
 * 콜 미디에이터가 바깥에 요구하는 것. 구현체는 `adapters/` 에 있고 `main.ts` 가 꽂는다.
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
  /** 화자 분리(`diarize`)를 켰을 때만 — 구글 화자 라벨. 누가 상담원인지는 채널이 정한다(`domain/diarization.ts`). */
  speakerLabel?: string;
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
  open(sampleRate: number, handlers: SttHandlers, options?: SttOpenOptions): SttStream;
}

export interface SttOpenOptions {
  /** 모노 한 줄의 두 화자를 가른다(`speaker=auto`). final 결과를 화자 구간마다 `speakerLabel` 을 붙여 나눠 보낸다. */
  diarize?: boolean;
}

// ── 서버 (hub) ──────────────────────────────────────────────────────────────

export interface CallStartRequest {
  call_id: string;
  stt_engine: string;
  channel_count: number;
  /** ⚠ 평문 발신 번호(C-5 P4). 서버가 곧바로 HMAC 으로 바꾼다(`decisions/304`). 이 콜 미디에이터는 로그에 남기지 않는다. */
  caller_phone?: string;
}

/**
 * J-5 인입 전 배정 판정(`decisions/126`·`313`). 통화 시작이 성공한 **직후** 부른다 — 서버가 발신 번호로 식별한 고객이
 * 블랙리스트면 근속 기준 이상 상담사를 고른다. `candidates` 는 「지금 받을 수 있는 상담사」인데 미디에이터는 대기 상태를
 * 모르므로 시연 설정 목록(`ROUTING_CANDIDATES`)을 넘긴다. 비면 서버가 기존 배정 규칙으로 떨어뜨린다.
 */
export interface RoutingDecisionRequest {
  call_id: string;
  candidates: string[];
}

/** `POST /hub/routing-decisions` 응답 그대로 — `{call_id, assigned_agent_id, is_blacklisted, fell_back, reason, …}`(값은 문자열, id 는 null 가능). */
export type RoutingDecisionPayload = Record<string, unknown>;

/** 마스킹 **전** 원문. 콜 미디에이터 → 서버로만 가고 그 밖으로는 나가지 않는다 (SEC-1). */
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
  /**
   * 이 콜 미디에이터가 STT final 을 **받은** 시각 — `utterance_end_ms` 와 같은 통화 시작 기준 ms.
   * 서버 트리거가 발동 시각으로 쓴다(없으면 «발화 종료 + 346ms» 모형). `w4-trigger-arrival-time`
   */
  received_at_ms: number;
}

export type RecommendPayload = Record<string, unknown>;

/** F-2 필요서류 자동 판정 — 그 통화 **상담원** 확정 발화의 **마스킹본**을 모아 보낸다. */
export interface RequiredDocsCheckRequest {
  call_id: string;
  procedure: string;
  agent_utterances: string[];
}

/** `POST /hub/required-docs-checks` 응답 그대로 — `plan.md` 7.3절 필요서류 체크리스트(값은 전부 문자열). */
export type ClosurePayload = Record<string, unknown> & { procedure: string };

/** C-6 콜 가드 검사 — **마스킹 후** 고객 발화만. 잡힌 표현이 그대로 저장·표시되기 때문이다(MANUAL-5.5). */
export interface CallGuardCheckRequest {
  call_id: string;
  segment_id: number;
  customer_utterance: string;
}

/** `POST /hub/call-guard-checks` 응답 그대로 — `{call_id, segment_id, flags: [{category, phrase, span, source_doc_id}]}`. */
export type CallGuardPayload = Record<string, unknown> & { flags: unknown[] };

/** C-1~C-4 컴플라이언스 검사 — **마스킹 후** 상담원 발화만(고객 발화는 C-6 몫). 판정은 서버 규칙이 한다. */
export interface ComplianceCheckRequest {
  call_id: string;
  segment_id: number;
  agent_utterance: string;
}

/** `POST /hub/compliance-checks` 응답 그대로 — `{call_id, segment_id, findings: [{rule_code, phrase, alternative_source?}]}`. 빈 배열은 「잡힌 것 없음」이지 「안전함」이 아니다(부록 A-1). */
export type CompliancePayload = Record<string, unknown> & { findings: unknown[] };

/**
 * 「검사 못 함」 — 상담원 발화 하나의 컴플라이언스 검사가 **서버에 닿지 못했거나 서버가 거절**했다. 위반이 없는 것과
 * 다르다(위반 없음은 아무 메시지도 안 보낸다). 화면은 이것을 「탐지 미동작」으로 보여야지 초록으로 두면 안 된다
 * (`w6-compliance-alert-ui` 완료 조건). `status` 는 HTTP 상태 문자열 — `"501"` 은 스포크 미등록(탐지 자체가 없다),
 * `"404"` 는 호출 순서(전사가 먼저 저장되지 않음), `"연결 실패"` 는 서버에 닿지 못함. 값은 전부 문자열(7.3절).
 */
export interface ComplianceUnavailable {
  call_id: string;
  segment_id: string;
  status: string;
}

export class HubError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "HubError";
    this.status = status;
  }
}

/**
 * `POST /hub/calls` 응답에서 콜 미디에이터가 쓰는 것. 서버는 같은 `call_id` 를 다시 받아도 행을 건드리지 않고(멱등),
 * **이미 저장된 가장 큰 발화 번호**를 돌려준다 — 통화를 다시 열면(파드 재시작·연결 끊김 뒤 재연결) 여기서 이어 센다.
 * 1부터 다시 세면 저장된 전사를 같은 번호로 덮어썼다(2026-09-22 운영 QA `test-qa-05`, `w6-segment-id-reuse`).
 */
export interface CallStartResult {
  /** 새 통화이거나 필드가 없는 옛 서버면 0 */
  lastSegmentId: number;
}

export interface HubPort {
  startCall(request: CallStartRequest): Promise<CallStartResult>;
  decideRouting(request: RoutingDecisionRequest): Promise<RoutingDecisionPayload>;
  ingestTranscript(raw: RawTranscript): Promise<MaskedTranscript>;
  recommend(request: RecommendRequest): Promise<RecommendPayload>;
  checkCallGuard(request: CallGuardCheckRequest): Promise<CallGuardPayload>;
  checkCompliance(request: ComplianceCheckRequest): Promise<CompliancePayload>;
  checkRequiredDocs(request: RequiredDocsCheckRequest): Promise<ClosurePayload>;
}

// ── 대시보드로 내보내기 ──────────────────────────────────────────────────────

/**
 * 「검색 중」 — 서버에 추천을 **요청했다**는 뜻이지 트리거가 발동했다는 뜻이 아니다(판정은 서버 몫).
 * 뒤따르는 `recommendation` 의 `fired` 가 `"false"` 면 대시보드가 로딩을 거둔다. 값은 전부 문자열(7.3절).
 */
export interface RecommendationPending {
  call_id: string;
  segment_id: string;
}

/**
 * 통화가 서버에 실제로 만들어졌다는 신호 — 통화당 한 번, 서버 `POST /hub/calls`가 성공한
 * 직후(`callFor()`)다. §7.3 계약엔 없던 메시지다 — 대시보드가 `call_id`를 잡을 곳이
 * 전사·추천·판정 이벤트뿐이라, 그 셋 중 아무것도 오기 전에 통화를 끝내면(맞장구만 있는
 * 아주 짧은 통화) `call_id`가 빈 채로 남아 `/close`가 404 났다(`w6-close-callid-missing`).
 */
export interface StartedPayload {
  call_id: string;
}

export type CallMediatorMessage =
  | { type: "transcript"; payload: MaskedTranscript }
  | { type: "started"; payload: StartedPayload }
  | { type: "recommendation_pending"; payload: RecommendationPending }
  | { type: "recommendation"; payload: RecommendPayload }
  | { type: "call_guard"; payload: CallGuardPayload }
  | { type: "compliance"; payload: CompliancePayload }
  | { type: "compliance_unavailable"; payload: ComplianceUnavailable }
  | { type: "closure"; payload: ClosurePayload }
  | { type: "routing_decision"; payload: RoutingDecisionPayload };

export interface Broadcaster {
  publish(callId: string, message: CallMediatorMessage): void;
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
