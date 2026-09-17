/**
 * 7.3절 인터페이스 계약 v2.
 * 정본: jekyll/docs/07-역할분담.markdown
 * domain 은 v3 보류 — optional 만 둔다.
 */

export type Speaker = "customer" | "agent";

export type MaskType = "P1" | "P2" | "P3" | "P4" | "P5" | "P6" | "P7";

/** 문자(코드포인트) 오프셋. span 은 [start, end) 반열린 구간. */
export interface MaskedSpan {
  type: MaskType;
  span: [number, number];
}

/**
 * 데모 도메인. decisions/201 이후 다산콜센터만 남긴다.
 * 옛 값 finance · shopping · health 는 유니온에서 뺐다 — ClosureType 과 달리
 * 화면 분기를 더 이상 만들지 않는다. 되돌리기는 git 이력.
 */
export type DemoDomain = "dasan";

/** 목록·이력 계약에서 쓰는 이름. 값은 DemoDomain 과 같다. */
export type Domain = DemoDomain;

export const DEMO_DOMAINS: readonly DemoDomain[] = ["dasan"];

export const DEMO_DOMAIN_LABELS: Record<DemoDomain, string> = {
  dasan: "다산콜센터",
};

/**
 * 금융·쇼핑 F-2 처리 유형.
 * 4도메인 시절 코드. decisions/201로 다산 단일화되며 신규 시나리오에는 쓰지 않는다.
 * `decisions/305`로 `ClosureEvent.closure_type` 필드 자체가 없어져 지금은 어디서도
 * 안 쓴다. 삭제하지 않는다 — 4도메인으로 되돌릴 가능성 대비 기록으로 남긴다.
 */
export type ClosureType = "상품해지" | "보상" | "반품" | "교환";

/**
 * 다산 민원 서비스명. 지식베이스 69종 실측이 오면 그 이름을 그대로 넣는다.
 * mock은 예시 서비스명만 쓴다 (`is_example`). `decisions/305`로 `ClosureEvent.procedure`가
 * 이 값(또는 조항 ID)을 받는다 — 타입 자체는 참고용으로 남긴다.
 */
export type RequiredDocsType = string;

/**
 * ⚠ 이 타입은 와이어 그대로가 아니라 **파싱 이후의 내부 표현**이다. 7.3절 규칙상
 * 실제 응답의 `is_final`·`utterance_end_ms`는 문자열(`"true"`·`"3100"`)로 온다 —
 * 그 경계는 `lib/ws/realCallMediatorClient.ts`의 `readBoolean`/`readNumber`,
 * `lib/api/coreClient.ts`의 `*Wire` 타입 + `toBool`/`toNum`이 따로 맡아서 여기 도달하기
 * 전에 이미 네이티브 타입으로 바뀐다. UI·mock은 전부 이 파싱 후 타입을 전제로 짜여
 * 있으므로, 필드를 `string`으로 바꾸는 건 계약을 맞추는 게 아니라 그 경계를 무너뜨리는
 * 것이다(2026-09-16 — 미결 항목의 "아직 boolean/number" 지적을 확인해보니 오판이었다).
 */
export interface TranscriptEvent {
  call_id: string;
  segment_id: string;
  speaker: Speaker;
  text: string;
  /**
   * mock 전용. 마스킹본 `text` 와 같은 길이의 원문.
   * 권한 확인 후 스팬 열람에만 쓴다. 7.3절 계약 필드는 아니다.
   */
  plain_text?: string;
  masked: MaskedSpan[];
  is_final: boolean;
  utterance_end_ms: number;
  domain?: DemoDomain;
}

/**
 * A-5 통번역 — §7.3 계약에 아직 없다. 프론트가 mock용으로 먼저 정의했다.
 * 고객 외국어 원문 + 한글 번역. original_lang 후보는 decisions/201 부록 A.
 */
export interface TranslatedUtterance {
  segment_id: number;
  original_text: string;
  original_lang: "vi" | "en" | "ja" | "zh" | "th";
  translated_text: string;
}

/**
 * A-5 상담원 한국어 → 고객 모국어 TTS. 실제 음성 재생은 이번 범위 밖.
 * 화면은 전송 상태만 표시한다. §7.3 미정.
 */
export interface AgentTtsStatus {
  segment_id: number;
  target_lang: string;
  status: "sent" | "pending";
}

/**
 * C-6 콜가드 — §7.3 계약에 아직 없지만 `category` 값은 백엔드
 * `server/apps/hub/app/dtos/call_guard_dto.py`(`CallGuardFlag`)를 그대로 따른다.
 * 옛 한글 3종(`폭언`·`욕설`·`위협`)은 여기서 걷어냈다 — `sexual`이 그 셋엔 없었고,
 * `distress`는 애초에 없었다.
 *
 * ⚠ **`distress`를 나머지 셋과 같은 자리에 두지만, 같은 취급을 하지 않는다.**
 * DASAN-MANUAL-5.4 — 위기 신호는 통화를 끊지 않고 전문 기관으로 연결한다(폭언과
 * 정반대). 화면·집계 양쪽에서 `isCallGuardDistress()`로 먼저 갈라 쓴다 —
 * `lib/blacklist/collectEvidence.ts`의 `abuseTotal()`이 이미 그렇게 한다.
 *
 * `severity`(low/high)는 프론트가 임시로 지어낸 필드였다 — 백엔드 DTO에 없고,
 * 부록 A-1(위험도 점수 금지)과도 어긋나 뺐다. `segment_id`는 계약 필드가 아니라
 * 프론트 저장소가 세그먼트별로 색인하려고 붙인 것이다.
 */
export interface CallGuardFlag {
  segment_id: number;
  category: "insult" | "threat" | "sexual" | "distress";
}

/** 위기 신호인가 — 화면·집계가 폭언과 반대로 다뤄야 하는 갈래다(MANUAL-5.4). */
export function isCallGuardDistress(flag: CallGuardFlag): boolean {
  return flag.category === "distress";
}

export interface DocumentSource {
  doc_id: string;
  title: string;
}

/** 자동 트리거(B-1)로 뜬 카드인지, 상담원이 직접 찾은 카드인지. */
export type CardSourceType = "auto" | "manual";

export interface RecommendationCard {
  title: string;
  summary: string;
  source: DocumentSource;
  similarity_score: number;
  /**
   * 7.3절 계약에는 아직 없다 — 수동 검색(B-6 보완 경로)을 화면에서 구분하려고
   * 프론트가 먼저 정의했다. 서버가 안 보내면 "auto" 로 본다.
   */
  source_type?: CardSourceType;
  /**
   * `decisions/308` — 카드 피드백(`POST /hub/cards/{card_id}/feedback`)에 쓴다.
   * DB에 연결되지 않은 카드는 서버가 null로 보낸다.
   */
  card_id?: string | null;
}

/**
 * 수동 검색 요청 — §2.3 B-6 으로 "관련 문서 없음"이 떴을 때 상담원이 직접 찾는 경로.
 * 서버 메시지 형식이 정해지면 7.3절로 올린다.
 */
export interface ManualSearchRequest {
  call_id: string;
  query: string;
}

export interface RecommendationBatch {
  /**
   * 트리거 발동 여부. `false` 면 검색조차 하지 않았다 — `cards`는 이때 빈 배열이다
   * (서버는 `null`을 보내지만 프론트는 "안 씀"과 "빈 배열"을 굳이 구분하지 않는다).
   * `fired: true, cards: []`(관련 문서 없음, B-6)와는 이 필드로만 구분된다.
   * `_project/decisions/401` — 서버 `RecommendResponse.fired`(필수 필드)를 그대로 받는다.
   */
  fired: boolean;
  call_id: string;
  trigger_at_ms: number;
  cards: RecommendationCard[];
  internal_latency_ms: number;
  domain?: DemoDomain;
}

/**
 * D 감정분석 기반 상담품질 평가. §7.3에 아직 없다 — 프론트가 mock용으로 먼저 정의했다.
 * 모델은 ai/(류준) 담당. 점수는 없다 — 정성 라벨과 C-6 건수만.
 */
export interface SentimentSummary {
  call_id: string;
  /** 통화 흐름 순 정성 라벨. 예: ["차분", "약간 격앙", "차분"] */
  trajectory: string[];
  /** 정밀 점수가 아니다. */
  overall: "양호" | "주의 필요";
  /** C-6 콜가드 경고 건수. 새로 만들지 않고 시나리오 callGuard 키 수를 쓴다. */
  guard_flag_count: number;
}

export interface LocalResource {
  orgName: string;
  address: string;
  phone: string;
}

/**
 * §2.5 D. 통화 후 처리 결과. 7.3절 계약에 아직 없다 — 프론트가 먼저 정의했다.
 * D-4(지식베이스 공백)는 이 통화에서 화면이 직접 관찰한 것이라 서버가 주지 않는다.
 * G-2 지역자원도 계약 전 — mock 목록만 붙인다.
 */
export interface CallWrapUp {
  call_id: string;
  /** D-1 상담 요약. 문장 단위. 화면에서는 한 문단으로 붙인다. */
  summary: string[];
  /** D-2 문의 유형. */
  category: string;
  /** D-2 태그. 없으면 category 한 개만 쓴다. */
  tags?: string[];
  /** D-3 후속조치 항목. */
  follow_ups: string[];
  /** G-2. 연계 가능한 지역자원. */
  local_resources?: LocalResource[];
  /** 확장 — 감정분석. 계약 확정 전 선택. */
  sentiment?: SentimentSummary;
}

/**
 * F-2 필요서류 체크리스트 판정값(`_project/decisions/305`, 2026-09-14).
 * 「차단」이 아니라 「경고」다(rev.5) — `complete`는 missing 이 비었다는 뜻.
 * 옛 `approved`/`blocked`는 여기서 걷어냈다(4도메인 시절 값, git 이력에 남아 있다).
 */
export type ClosureVerdict = "complete" | "incomplete";

/**
 * `_project/decisions/305` — `closure_type`(4도메인 처리유형)·`approved`/`blocked`를
 * 걷어내고 `procedure`(필요서류 조항 ID·추천 카드 `source.doc_id`와 같은 체계) +
 * `verdict: complete/incomplete`로 바꿨다. 계약 예시(`server/apps/hub/app/dtos/closure_verdict_dto.py`):
 * `{"call_id","procedure","procedure_title","evidence","verdict","missing","source","detected"}`.
 * 값은 전부 문자열로 온다(다른 계약 3종과 같다) — 파싱은 `lib/ws/realCallMediatorClient.ts`가 한다.
 */
export interface ClosureEvent {
  call_id: string;
  /** 필요서류 조항 ID(`DASAN-TERM-4.4`) 또는 다산 서비스명. 옛 closure_type을 대체한다. */
  procedure: string;
  /** 조항 제목. 서버가 안 보내면 화면은 procedure 값을 그대로 쓴다. */
  procedure_title?: string;
  reason?: string | null;
  /** 키 = 이 절차에 필요한 서류 하나 → 안내했는가. */
  evidence: Record<string, boolean>;
  verdict: ClosureVerdict;
  /** 상담원이 아직 안내하지 않은 필수 서류 — 빠짐없이. */
  missing: string[];
  /** 조건부 추가 서류 — 판정에는 넣지 않는다. 「해당하면 함께」로만 보여준다. */
  conditional?: string[];
  source?: DocumentSource;
  /** true면 상담원 발화 키워드로 자동 판정했다 — 부정 문맥을 모른다. */
  detected: boolean;
  domain?: DemoDomain;
  /**
   * 프론트 전용. 69종 구비서류 실측이 지식베이스에 오기 전 mock임을 표시한다.
   * 서버가 안 보내면 예시로 보지 않는다.
   */
  is_example?: boolean;
}

export function hasCardSource(card: RecommendationCard): boolean {
  return card.source.doc_id.length > 0 && card.source.title.length > 0;
}

export function cardSourceType(card: RecommendationCard): CardSourceType {
  return card.source_type === "manual" ? "manual" : "auto";
}

/**
 * 통화 목록 한 줄. 목록 API(`GET /hub/calls`)는 아직 계약에 없다.
 * 자막 재조회는 `GET /hub/calls/{call_id}/transcript` 가 있다.
 */
export interface CallHistoryItem {
  call_id: string;
  started_at: string;
  domain: Domain;
  inquiry_type: string;
  customer_ref: string;
  /** A-5. 외국어 통화만. 화면 LanguageBadge 와 상담기록 국기를 맞춘다. */
  targetLanguage?: "VI" | "EN" | "JA" | "ZH" | "TH";
}

/**
 * 자막 재조회 세그먼트. `TranscriptEvent.segment_id` 는 아직 string
 * (팀 결정 대기). 이 타입만 백엔드 `TranscriptSegmentSchema` 의 number 를 따른다.
 *
 * ⚠ 이것도 파싱 이후 내부 표현이다(위 `TranscriptEvent` 주석 참고) — 와이어 형식은
 * `coreClient.ts`의 `TranscriptSegmentWire`(`is_final: string`·`utterance_end_ms: string
 * | null`)이고 `toBool`/`toNum`이 여기 오기 전에 변환한다.
 */
export interface TranscriptQuerySegment {
  segment_id: number;
  speaker: Speaker;
  text: string;
  plain_text?: string;
  masked: MaskedSpan[];
  is_final: boolean;
  utterance_end_ms: number | null;
}

export interface TranscriptPage {
  call_id: string;
  segments: TranscriptQuerySegment[];
  total: number;
  limit: number;
  offset: number;
}

/* ─────────────────────────────────────────────────────────────────────────
 * J — 콜 라우팅 보호 (`_project/decisions/204`, 2026-09-09)
 *
 * C-6 이 통화 **중** 폭언을 경고한다면, J 는 **다음 통화**를 다루는 경로다.
 * §7.3 계약에 아직 없다 — 백엔드 DTO(`server/apps/hub/app/dtos/blacklist_dto.py`)와
 * 같은 모양으로 먼저 맞춰 뒀다. 계약이 확정되면 그쪽을 정본으로 삼는다.
 * ───────────────────────────────────────────────────────────────────────── */

/**
 * **요청의 상태만** 담는다(2026-09-09, `_project/decisions/205` ②).
 * 해제(`released`)는 **등록**(`BlacklistEntryItem.released_at`)의 상태이지 요청의 상태가
 * 아니다 — 두 곳에 두었더니 한쪽만 갱신돼 관리창이 「승인」과 「해제됨」을 동시에
 * 보여주는 상태가 실제로 나왔다.
 */
export type BlacklistStatus = "pending" | "approved" | "rejected";

/**
 * 관리자가 **통화를 다시 듣지 않고** 판단할 수 있게 싣는 근거.
 * ⚠ 전부 셀 수 있는 건수다 — 위험도 점수를 만들지 않는다(부록 A-1).
 */
export interface BlacklistEvidence {
  call_duration_s: number;
  insult_count: number;
  threat_count: number;
  sexual_count: number;
  /**
   * ⚠ **블랙리스트 사유가 아니고, 서버에 저장되지도 않는다**(`decisions/205` ④).
   * DASAN-MANUAL-5.4 — 자해·극단적 선택 암시는 폭언과 다르게 다룬다. 도움이 필요한
   * 사람을 차단 대상으로 올리는 것은 정반대 방향이다.
   *
   * 자해 암시 건수는 **정신건강에 관한 정보**라 고객 식별자와 같은 행에 무기한 남기면
   * 「이 사람이 자해를 N회 암시했다」는 레코드가 된다. 그래서 `blacklist_request` 에
   * 대응 컬럼이 없다 — 이 값은 **요청 화면의 경고를 띄우기 위한 일회성 값**이다.
   */
  distress_count: number;
  /** D-5 통화 온도 이상 구간 수(`decisions/203`). 점수가 아니라 건수다. */
  temperature_outliers: number;
}

export interface BlacklistRequestItem {
  request_id: string;
  call_id: string;
  /**
   * ⚠ **전화번호의 HMAC 이다. 평문을 넣지 않는다**(`decisions/205` ③) — 전화번호는
   * C-5 의 P4 이고, 자막에서 지운 값을 여기 평문으로 두면 마스킹을 앞단에 둔 의미가
   * 사라진다. 화면 표시는 `display_hint` 를 쓴다.
   */
  customer_ref: string;
  /** 화면 표시 전용(뒤 4자리 등). 조회·배정은 `customer_ref` 로만 한다. */
  display_hint: string;
  requested_by: string;
  reason: string;
  /** ⚠ **마스킹된 자막**이다. 원문이 아니다 — DASAN-MANUAL-5.5 · C-5. */
  context_excerpt: string;
  evidence: BlacklistEvidence;
  status: BlacklistStatus;
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  /** 위 건수를 집계한 시각. DB `blacklist_request.evidence_snapshot_at`(2026-09-09 스키마). */
  evidence_snapshot_at: string;
}

/**
 * 등록 **에피소드** 1건. 「고객 1명 = 1행」이 아니다(`decisions/205` ②) —
 * 해제 후 재등록되면 행이 하나 더 생기고 옛 행은 `released_at` 이 찍힌 채 남는다.
 */
export interface BlacklistEntryItem {
  entry_id: string;
  customer_ref: string;
  /**
   * ⚠ **DB `blacklist_entry` 테이블엔 이 컬럼이 없다**(2026-09-09 스키마 — ERD 대조로 발견).
   * 표시용 힌트는 등록이 아니라 요청(`BlacklistRequestItem.display_hint`)에만 있다 —
   * `request_id`로 원 요청을 찾아 붙인다.
   */
  request_id: string;
  approved_at: string;
  /** 만료가 없으면 영구 표시가 된다(`decisions/205` ⑤). */
  expires_at: string;
  released_at: string | null;
  released_by: string | null;
  release_reason: string | null;
  /** **관리자 승인 메모.** 요청 사유의 사본이 아니다 — 사본을 두면 같은 개인정보가 두 벌이 된다. */
  note: string | null;
}
