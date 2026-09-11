import type {
  CallWrapUp,
  ClosureEvent,
  ManualSearchRequest,
  RecommendationBatch,
  TranscriptEvent,
  TranslatedUtterance,
  AgentTtsStatus,
  CallGuardFlag,
} from "../../types/contract";
import type { TargetLanguage } from "../language/languageMeta";

export interface GatewayListener {
  onTranscript: (event: TranscriptEvent) => void;
  onRecommendation: (event: RecommendationBatch) => void;
  /**
   * 카드 추천 요청이 나가 응답을 기다리는 중임을 알린다 — §7.3 계약에 없다.
   * mock만 보낸다(트리거 발동 시점에 쏘고 internal_latency_ms 뒤 onRecommendation).
   * 실서버는 아직 이 신호가 없어 로딩 인디케이터가 뜨지 않는다 — 계약이 생기면 연결한다.
   */
  onRecommendationPending?: (callId: string) => void;
  onClosure: (event: ClosureEvent) => void;
  onStatus: (status: GatewayStatus) => void;
  onError: (message: string) => void;
  /** A-5. §7.3 미정 — mock만 보낸다. 키는 자막 segment_id. */
  onTranslation?: (
    transcriptSegmentId: string,
    event: TranslatedUtterance,
  ) => void;
  onAgentTts?: (transcriptSegmentId: string, event: AgentTtsStatus) => void;
  /** C-6. §7.3 미정 — mock만 보낸다. 키는 자막 segment_id. */
  onCallGuard?: (transcriptSegmentId: string, event: CallGuardFlag) => void;
  /** A-5 ⓑ. 번역이 아님. 키만 보낸다. 점수는 없다. */
  onAccentRecognition?: (transcriptSegmentId: string) => void;
  /** A-5. 통화 시작 시 대상 언어. 한국어 전용 mock은 null. */
  onCallLanguage?: (lang: TargetLanguage | null) => void;
}

export type GatewayMode = "mock" | "live";

export interface GatewayStatus {
  mode: GatewayMode;
  connected: boolean;
}

export interface GatewayClient {
  readonly mode: GatewayMode;
  connect(listeners: GatewayListener): void;
  disconnect(): void;
  /**
   * 상담원이 직접 검색한다(B-6 보완 경로). 자동 추천과 달리 요청·응답이 1:1 이라
   * 리스너가 아니라 Promise 로 돌려준다. 결과가 없으면 cards 가 빈 배열이다 —
   * 없는 것을 채워 보내지 않는다.
   */
  manualSearch(request: ManualSearchRequest): Promise<RecommendationBatch>;
  /** §2.5 D-1~D-3 통화 후 처리. 계약 미정 — manualSearch 와 같은 이유로 Promise 다. */
  wrapUp(callId: string): Promise<CallWrapUp>;
}

const GATEWAY_URL_STORAGE_KEY = "callguard:gatewayUrlOverride";

/**
 * 빌드타임 환경변수(VITE_GATEWAY_WS_URL)는 Vercel 프로젝트 설정 접근 권한이
 * 있어야 바꿀 수 있다. 배포 담당자 협조 없이도 개발자 본인이 배포된
 * 대시보드를 라이브 모드로 테스트할 수 있게, ?gateway=<wss URL> 쿼리로
 * 방문하면 localStorage 에 저장해 다음 방문부터도 유지되는 런타임 탈출구를
 * 둔다. ?gateway=clear 로 지우면 원래 설정(mock 또는 빌드타임 환경변수)으로
 * 돌아간다(2026-09-11).
 */
function syncGatewayOverrideFromQuery(): void {
  if (typeof window === "undefined") {
    return;
  }
  const raw = new URLSearchParams(window.location.search).get("gateway");
  if (raw === null || raw.trim().length === 0) {
    return;
  }
  const value = raw.trim();
  try {
    if (value === "clear") {
      window.localStorage.removeItem(GATEWAY_URL_STORAGE_KEY);
    } else if (value.startsWith("ws://") || value.startsWith("wss://")) {
      window.localStorage.setItem(GATEWAY_URL_STORAGE_KEY, value);
    }
  } catch {
    // localStorage 를 못 쓰는 환경(프라이빗 모드 등)이면 이번 방문에서만 쿼리값이 적용된다.
  }
}

function readGatewayOverride(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(GATEWAY_URL_STORAGE_KEY);
    return stored !== null && stored.length > 0 ? stored : null;
  } catch {
    return null;
  }
}

export function gatewayUrl(): string {
  syncGatewayOverrideFromQuery();
  const override = readGatewayOverride();
  if (override !== null) {
    return override;
  }
  return (import.meta.env.VITE_GATEWAY_WS_URL ?? "").trim();
}

export function isLiveGatewayConfigured(): boolean {
  return gatewayUrl().length > 0;
}
