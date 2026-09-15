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

/** `wrapUp`에 실어 보낼 자막 한 줄. `store/callStore.ts`의 `Utterance`와 같은 모양이다. */
export interface WrapUpSegment {
  segment_id: string;
  speaker: "customer" | "agent";
  text: string;
  is_final: boolean;
  utterance_end_ms: number;
}

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
  /**
   * §2.5 D-1~D-3 통화 후 처리. `decisions/306` — `POST /hub/calls/{id}/close`.
   * `segments`는 이번 통화에서 쌓인 자막 전부(마스킹 완료본, SEC-1)다.
   */
  wrapUp(callId: string, segments: WrapUpSegment[]): Promise<CallWrapUp>;
}

const GATEWAY_URL_STORAGE_KEY = "callguard:gatewayUrlOverride";

// 정식 게이트웨이(decisions/109)와 로컬 개발만 허용한다. 그 밖의 주소를 받으면
// ?gateway= 링크 하나로 아무 서버에 붙여 가짜 자막·가짜 "필요서류" 카드를
// 상담원에게 보여줄 수 있다(2026-09-11 open-items 지적, 실제 운영 번들에서 확인됨).
const ALLOWED_LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

function isAllowedGatewayUrl(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false; // URL로 못 읽으면(ws/wss 스킴이라도) 거른다
  }
  if (parsed.protocol === "wss:") {
    return (
      parsed.hostname === "server.solidbob.cloud" &&
      parsed.pathname.startsWith("/gateway")
    );
  }
  if (parsed.protocol === "ws:") {
    return ALLOWED_LOCAL_HOSTS.has(parsed.hostname);
  }
  return false;
}

/**
 * 빌드타임 환경변수(VITE_GATEWAY_WS_URL)는 Vercel 프로젝트 설정 접근 권한이
 * 있어야 바꿀 수 있다. 배포 담당자 협조 없이도 개발자 본인이 배포된
 * 대시보드를 라이브 모드로 테스트할 수 있게, ?gateway=<wss URL> 쿼리로
 * 방문하면 localStorage 에 저장해 다음 방문부터도 유지되는 런타임 탈출구를
 * 둔다. ?gateway=clear 로 지우면 원래 설정(mock 또는 빌드타임 환경변수)으로
 * 돌아간다(2026-09-11). **허용 목록을 통과한 주소만** 저장한다(2026-09-14) —
 * `server.solidbob.cloud/gateway/*`(정식 게이트웨이)와 로컬 개발(`ws://localhost`·
 * `ws://127.0.0.1`)뿐이다.
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
    } else if (isAllowedGatewayUrl(value)) {
      window.localStorage.setItem(GATEWAY_URL_STORAGE_KEY, value);
    }
    // 허용 목록에 없는 주소는 조용히 버린다 — 에러를 띄우면 그 자체가 "여기 그런
    // 기능이 있다"는 스캔 힌트가 된다.
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

/** 지금 저장된 override 주소 — 배너가 "어디에 붙었는지" 보여줄 때 쓴다. */
export function gatewayOverrideUrl(): string | null {
  return readGatewayOverride();
}

/** 배너의 "연결 해제" 버튼이 부른다. 빌드타임 설정(또는 mock)으로 되돌린다. */
export function clearGatewayOverride(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(GATEWAY_URL_STORAGE_KEY);
  } catch {
    // 못 지워도 다음 탭/새로고침에서 다시 시도할 수 있다
  }
}
