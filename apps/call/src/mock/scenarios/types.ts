import type { TargetLanguage } from "../../lib/language/languageMeta";
import type {
  AgentTtsStatus,
  CallGuardFlag,
  CallWrapUp,
  ClosureEvent,
  SentimentSummary,
  DemoDomain,
  RecommendationBatch,
  TranscriptEvent,
  TranslatedUtterance,
} from "../../types/contract";

export interface ScheduledClosure {
  /** 이 발화가 나간 뒤에 종결 이벤트를 재생한다. */
  afterSegmentId: string;
  event: ClosureEvent;
}

export interface MockScenario {
  domain: DemoDomain;
  /** A-5. 외국어 통화만. 한국어 전용 시나리오는 두지 않는다. */
  targetLanguage?: TargetLanguage;
  transcripts: TranscriptEvent[];
  cardBatches: RecommendationBatch[];
  closures: ScheduledClosure[];
  /**
   * A-5 mock. 키는 TranscriptEvent.segment_id. §7.3 에 이벤트가 없어
   * 시나리오에 붙여 재생한다.
   */
  translations?: Record<string, TranslatedUtterance>;
  agentTts?: Record<string, AgentTtsStatus>;
  /**
   * A-5 ⓑ. 고객이 한국어로 직접 말한다. 번역 이벤트가 아니다.
   * 고객 자막에 「억양 인식」만 붙인다. 신뢰도 점수는 없다.
   */
  accentRecognition?: boolean;
  /** C-6 mock. 키는 TranscriptEvent.segment_id. 경고만, 통화는 끊지 않는다. */
  callGuard?: Record<string, CallGuardFlag>;
  /**
   * §2.5 D-1~D-3. 요약·분류 모델이 아직 없어 손으로 적어둔 것이다.
   * 재생되는 transcripts 와 어긋나면 데모가 거짓말을 하게 되므로 같이 고친다.
   */
  wrapUp: Omit<CallWrapUp, "call_id" | "sentiment">;
  /**
   * D 감정분석 mock. 궤적 라벨만 적는다. overall·건수는 wrapUp 때 callGuard에서 채운다.
   */
  sentiment?: Pick<SentimentSummary, "trajectory">;
}
