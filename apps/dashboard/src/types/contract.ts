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
 * 삭제하지 않는다 — 4도메인으로 되돌릴 가능성 대비 기록으로 남긴다.
 */
export type ClosureType = "상품해지" | "보상" | "반품" | "교환";

/**
 * 다산 민원 서비스명. 지식베이스 69종 실측이 오면 그 이름을 그대로 넣는다.
 * mock은 예시 서비스명만 쓴다 (`is_example`).
 */
export type RequiredDocsType = string;

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
 * C-6 콜가드 — §7.3 계약에 아직 없다. 프론트가 mock용으로 먼저 정의했다.
 * 고객 발화 텍스트만 본다. 오디오 톤·자동 차단은 decisions/201 범위 밖.
 */
export interface CallGuardFlag {
  segment_id: number;
  category: "폭언" | "욕설" | "위협";
  severity: "low" | "high";
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
  call_id: string;
  trigger_at_ms: number;
  cards: RecommendationCard[];
  internal_latency_ms: number;
  e2e_latency_ms: number;
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
 * 4도메인 시절 F-2 판정값. decisions/201로 다산 단일화되며 화면 카피는 쓰지 않는다.
 * DTO를 재사용하므로 필드는 남긴다 — approved 는 missing 이 비었다는 뜻.
 */
export type ClosureVerdict = "approved" | "blocked";

export interface ClosureEvent {
  call_id: string;
  /** 금융·쇼핑이면 ClosureType, 다산이면 서비스명(RequiredDocsType). */
  closure_type: ClosureType | RequiredDocsType;
  reason: string;
  /** 키 = 종결 요건 항목 → 다산에서는 이 서비스에 필요한 서류 하나. */
  evidence: Record<string, boolean>;
  verdict: ClosureVerdict;
  /** 상담원이 아직 안내하지 않은 서류(다산) / 미충족 종결 항목(4도메인). */
  missing: string[];
  source: DocumentSource;
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
